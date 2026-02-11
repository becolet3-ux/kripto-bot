
import os
import sys
import pandas as pd
import numpy as np
import logging

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from ml.ensemble_manager import EnsembleManager

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Trainer")

def create_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates target labels based on future price movements.
    """
    logger.info("Generating labels from historical data...")
    
    # Sort by symbol and time
    df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
    df = df.sort_values(['symbol', 'timestamp'])
    
    # Group by symbol
    df['next_close'] = df.groupby('symbol')['close'].shift(-1)
    
    # Calculate return
    df['return'] = (df['next_close'] - df['close']) / df['close']
    
    # Define Target: 1 if return > 0.2% (commission cover), else 0
    # You can adjust this threshold (e.g. 0.005 for 0.5%)
    THRESHOLD = 0.002
    df['Target'] = (df['return'] > THRESHOLD).astype(int)
    
    # Drop rows with NaN (last row of each symbol)
    df = df.dropna(subset=['next_close'])
    
    logger.info(f"Labels generated. Positive samples: {df['Target'].sum()} / {len(df)}")
    return df

def main():
    logger.info("Starting Model Training...")
    
    # Check data file
    data_path = os.path.join(os.getcwd(), 'data', 'ml_training_data.csv')
    if not os.path.exists(data_path):
        logger.error(f"Training data not found at {data_path}")
        return

    # Load Data
    try:
        logger.info(f"Loading data from {data_path}...")
        # Use on_bad_lines='skip' to handle corrupted rows
        df = pd.read_csv(data_path, on_bad_lines='skip', engine='python')
        logger.info(f"Data loaded: {len(df)} rows")
        
        # Use only last 50k rows to avoid OOM on small servers
        if len(df) > 50000:
            logger.info("Trimming data to last 50,000 rows for memory safety...")
            df = df.iloc[-50000:]
            
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return
        
    # Check if we need to label the data
    if 'Target' not in df.columns:
        if 'close' in df.columns and 'symbol' in df.columns:
            df = create_labels(df)
        else:
            logger.error("Data missing 'close' or 'symbol' columns, cannot generate labels.")
            return

    # Initialize Ensemble Manager
    # Ensure models directory exists
    models_dir = os.path.join(os.getcwd(), 'models')
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
        logger.info(f"Created models directory at {models_dir}")

    ensemble = EnsembleManager(models_dir=models_dir)
    
    if not ensemble.models:
        logger.error("No ML models available (sklearn missing?).")
        return

    logger.info(f"Training models using target: Target")
    metrics = ensemble.train(df, target_col='Target')
    
    logger.info("Training complete!")
    logger.info(f"Metrics: {metrics}")

if __name__ == "__main__":
    main()
