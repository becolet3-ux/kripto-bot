
import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

# ML Libraries
from sklearn.ensemble import RandomForestClassifier
try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None
try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, classification_report

logger = logging.getLogger("EnsembleManager")

class EnsembleManager:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)
            
        self.models = {
            'rf': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        }
        
        if XGBClassifier:
            self.models['xgb'] = XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, eval_metric='logloss')
        
        if LGBMClassifier:
            self.models['lgbm'] = LGBMClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, verbose=-1)

        
        self.is_trained = False
        self.feature_columns = [
            'RSI', 'MACD', 'MACD_Signal', 'CCI', 'ADX', 'MFI', 
            'Stoch_RSI_K', 'Stoch_RSI_D', 'Williams_R', 
            'ATR', 'Bollinger_Upper', 'Bollinger_Lower',
            'SMA_50', 'SMA_200', 'VWAP'
        ]
        
        self.load_models()

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extracts and normalizes features from the dataframe.
        """
        # Ensure we have all columns
        missing_cols = [col for col in self.feature_columns if col not in df.columns]
        if missing_cols:
            # If columns are missing, return empty or handle gracefully
            # For now, we assume analyzer.py provides these.
            # We might need to compute ratios instead of raw values for some.
            pass

        # Create a copy to avoid SettingWithCopy warnings
        X = df.copy()
        
        # Feature Engineering: Convert raw values to ratios/normalized forms where appropriate
        # This makes the model more robust to price scale differences
        if 'close' in X.columns:
            if 'SMA_50' in X.columns:
                X['SMA_50_Ratio'] = X['close'] / X['SMA_50']
            if 'SMA_200' in X.columns:
                X['SMA_200_Ratio'] = X['close'] / X['SMA_200']
            if 'Bollinger_Upper' in X.columns:
                X['BB_Upper_Dist'] = (X['Bollinger_Upper'] - X['close']) / X['close']
            if 'Bollinger_Lower' in X.columns:
                X['BB_Lower_Dist'] = (X['close'] - X['Bollinger_Lower']) / X['close']
            if 'VWAP' in X.columns:
                X['VWAP_Ratio'] = X['close'] / X['VWAP']
                
        # Update feature list to use engineered features
        # For this first version, we'll mix raw indicators (RSI, ADX are scale-independent)
        # with engineered price ratios.
        
        final_features = [
            'RSI', 'MACD', 'CCI', 'ADX', 'MFI', 
            'Stoch_RSI_K', 'Stoch_RSI_D', 'Williams_R', 
            'SMA_50_Ratio', 'SMA_200_Ratio', 
            'BB_Upper_Dist', 'BB_Lower_Dist',
            'VWAP_Ratio'
        ]
        
        # Check availability again
        available_features = [f for f in final_features if f in X.columns]
        
        return X[available_features].fillna(0)

    def save_snapshot(self, df: pd.DataFrame, symbol: str):
        """
        Saves the current market state (features) for future training.
        """
        try:
            X = self.prepare_features(df)
            if X.empty:
                return
                
            last_row = X.iloc[[-1]].copy()
            last_row['timestamp'] = int(datetime.now().timestamp())
            last_row['symbol'] = symbol
            last_row['close'] = df['close'].iloc[-1]
            
            # Save to CSV
            data_file = os.path.join(os.getcwd(), 'data', 'ml_training_data.csv')
            
            # Check if header is needed
            header = not os.path.exists(data_file)
            
            last_row.to_csv(data_file, mode='a', header=header, index=False)
        except Exception as e:
            logger.error(f"Snapshot kaydetme hatası: {e}")

    def train(self, df: pd.DataFrame, target_col: str = 'Target'):
        """
        Trains the ensemble models.
        Target should be 1 (Buy/Up) or 0 (Sell/Down/Neutral).
        """
        X = self.prepare_features(df)
        y = df[target_col]
        
        if len(X) < 50:
            logger.warning("Yetersiz veri, eğitim atlandı.")
            return
            
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        logger.info(f"Model eğitimi başlıyor. Veri seti: {len(X)} satır.")
        
        metrics = {}
        
        for name, model in self.models.items():
            try:
                model.fit(X_train, y_train)
                preds = model.predict(X_test)
                acc = accuracy_score(y_test, preds)
                metrics[name] = acc
                logger.info(f"{name} accuracy: {acc:.4f}")
                
                # Save model
                joblib.dump(model, os.path.join(self.models_dir, f"{name}_model.pkl"))
            except Exception as e:
                logger.error(f"{name} eğitimi başarısız: {e}")
        
        self.is_trained = True
        logger.info("Ensemble eğitimi tamamlandı.")
        return metrics

    def predict_proba(self, df: pd.DataFrame) -> float:
        """
        Returns the ensemble probability score (0.0 to 1.0) for the *last* row of the dataframe.
        """
        if not self.is_trained:
            return 0.5 # Neutral
            
        X = self.prepare_features(df)
        if X.empty:
            return 0.5
            
        # Take the last row (current market state)
        last_row = X.iloc[[-1]]
        
        probas = []
        for name, model in self.models.items():
            try:
                # Class 1 is 'Buy' usually
                p = model.predict_proba(last_row)[0][1]
                probas.append(p)
            except Exception as e:
                logger.error(f"Tahmin hatası ({name}): {e}")
                
        if not probas:
            return 0.5
            
        # Soft Voting (Average)
        avg_proba = sum(probas) / len(probas)
        return avg_proba

    def load_models(self):
        loaded_count = 0
        for name in self.models.keys():
            path = os.path.join(self.models_dir, f"{name}_model.pkl")
            if os.path.exists(path):
                try:
                    self.models[name] = joblib.load(path)
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Model yüklenemedi ({name}): {e}")
        
        if loaded_count == len(self.models):
            self.is_trained = True
            logger.info("Tüm modeller başarıyla yüklendi.")
        elif loaded_count > 0:
            self.is_trained = True
            logger.warning(f"{loaded_count}/{len(self.models)} model yüklendi.")
        else:
            logger.info("Henüz eğitilmiş model bulunamadı.")

