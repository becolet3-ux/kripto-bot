import json
import os
import time
from typing import Dict, Optional

class BotBrain:
    def __init__(self, data_file="data/learning_data.json"):
        self.data_file = data_file
        self.memory = self._load_memory()
        
    def _load_memory(self) -> Dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Ensure indicator_weights exists (Migration)
                    if "indicator_weights" not in data:
                        data["indicator_weights"] = {
                            "rsi": 1.0,
                            "macd": 1.0,
                            "super_trend": 1.0,
                            "sma_trend": 1.0,
                            "bollinger": 1.0,
                            "stoch_rsi": 1.0,
                            "cci": 1.0,
                            "adx": 1.0
                        }
                    else:
                        # Ensure new keys exist in existing dictionary
                        defaults = {
                            "rsi": 1.0, "macd": 1.0, "super_trend": 1.0,
                            "sma_trend": 1.0, "bollinger": 1.0, "stoch_rsi": 1.0,
                            "cci": 1.0, "adx": 1.0, "mfi": 1.0, "patterns": 1.0
                        }
                        for k, v in defaults.items():
                            if k not in data["indicator_weights"]:
                                data["indicator_weights"][k] = v
                                
                    return data
            except:
                pass
        return {
            "coin_performance": {},  # symbol -> {wins: 0, losses: 0, consecutive_losses: 0, last_loss_time: 0}
            "global_stats": {"total_trades": 0, "wins": 0, "win_rate": 0.0},
            "trade_history": [],  # List of last N trades with features
            "strategy_weights": {
                "trend_following": 1.0,
                "golden_cross": 1.0,
                "oversold_bounce": 1.0,
                "volume_breakout": 1.0
            },
            "ghost_trades": [], # Active virtual trades to track missed opportunities
            "indicator_weights": {
                "rsi": 1.0,
                "macd": 1.0,
                "super_trend": 1.0,
                "sma_trend": 1.0,
                "bollinger": 1.0,
                "stoch_rsi": 1.0,
                "cci": 1.0,
                "adx": 1.0,
                "mfi": 1.0,
                "patterns": 1.0
            }
        }

    def _save_memory(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.memory, f, indent=4)

    def get_weights(self) -> Dict[str, float]:
        """Returns current strategy weights"""
        return self.memory.get("strategy_weights", {
            "trend_following": 1.0,
            "golden_cross": 1.0,
            "oversold_bounce": 1.0,
            "volume_breakout": 1.0
        })

    def get_indicator_weights(self) -> Dict[str, float]:
        """Returns current indicator weights"""
        return self.memory.get("indicator_weights", {
            "rsi": 1.0,
            "macd": 1.0,
            "super_trend": 1.0,
            "sma_trend": 1.0,
            "bollinger": 1.0,
            "stoch_rsi": 1.0,
            "cci": 1.0,
            "adx": 1.0,
            "mfi": 1.0,
            "patterns": 1.0
        })

    def get_risk_regime(self) -> Dict[str, float]:
        """
        Determines current risk regime based on recent performance.
        Returns a dict with 'max_position_multiplier' and 'stop_loss_multiplier'.
        """
        stats = self.memory.get("global_stats", {})
        total_trades = stats.get("total_trades", 0)
        
        # Default: Normal Mode
        regime = {
            "name": "NORMAL",
            "max_pos_multiplier": 1.0,
            "stop_loss_multiplier": 1.0
        }
        
        if total_trades < 5:
            return regime
            
        # Check last 5 trades for consecutive losses
        history = self.memory.get("trade_history", [])
        last_5 = history[-5:]
        losses = [t for t in last_5 if t.get('pnl', 0) < 0]
        
        # Defensive Mode: If 3+ losses in last 5 trades or big recent drawdown
        if len(losses) >= 3:
            regime = {
                "name": "DEFENSIVE",
                "max_pos_multiplier": 0.5, # Halve the position size
                "stop_loss_multiplier": 0.8 # Tighter stop loss (e.g. 5% -> 4%)
            }
        
        return regime

    def update_indicator_weights(self, indicator_signals: Dict[str, int], pnl_pct: float):
        """
        Updates indicator weights based on their individual contribution correctness.
        indicator_signals: { 'rsi': 1, 'macd': -1, ... } (1: Bullish, -1: Bearish, 0: Neutral)
        pnl_pct: Trade profit/loss percentage
        """
        weights = self.get_indicator_weights()
        lr = 0.02 # Slower learning rate for indicators to avoid noise

        # Direction of the trade (Assuming LONG only bot for now)
        # If we had SHORT, we would need trade_direction parameter.
        # For Spot/Long-Only: Win means Up, Loss means Down.
        
        is_win = pnl_pct > 0
        
        for ind, signal in indicator_signals.items():
            if ind not in weights:
                weights[ind] = 1.0
                
            if signal == 0:
                continue # Neutral, didn't contribute
                
            # Logic:
            # If Win (Price went UP) AND Signal was 1 (Bullish) -> Reward
            # If Win (Price went UP) AND Signal was -1 (Bearish) -> Penalty (It was wrong)
            # If Loss (Price went DOWN) AND Signal was 1 (Bullish) -> Penalty (It was wrong)
            # If Loss (Price went DOWN) AND Signal was -1 (Bearish) -> Reward (It was right to be bearish)
            
            reward = False
            if is_win:
                if signal == 1: reward = True
                elif signal == -1: reward = False
            else: # Loss
                if signal == 1: reward = False
                elif signal == -1: reward = True
            
            if reward:
                weights[ind] *= (1 + lr)
            else:
                weights[ind] *= (1 - lr)
                
            # Clamp weights (0.2x to 5.0x) - Allow wider range for indicators
            weights[ind] = max(0.2, min(weights[ind], 5.0))
            
        self.memory["indicator_weights"] = weights
        return weights

    def update_weights(self, strategy: str, pnl_pct: float):
        """Updates strategy weights based on trade outcome (Reinforcement Learning)"""
        weights = self.get_weights()
        if strategy not in weights:
            weights[strategy] = 1.0
            
        # Learning Rate
        lr = 0.05 
        
        # Reward/Penalty Logic
        if pnl_pct > 0:
            # Increase weight: reward
            weights[strategy] *= (1 + lr)
        else:
            # Decrease weight: penalty
            weights[strategy] *= (1 - lr)
            
        # Clamp weights to avoid extreme bias (0.5x to 3.0x)
        weights[strategy] = max(0.5, min(weights[strategy], 3.0))
        
        self.memory["strategy_weights"] = weights
        self._save_memory()
        return f"Weight updated for {strategy}: {weights[strategy]:.2f}"

    def record_outcome(self, symbol: str, pnl_pct: float, entry_features: Dict, entry_price: float = 0.0, exit_price: float = 0.0):
        """
        İşlem sonucunu kaydeder ve 'beyni' günceller.
        """
        timestamp = int(time.time())
        is_win = pnl_pct > 0
        
        # 0. Update Strategy Weights (Adaptive Learning)
        strategy_name = entry_features.get('strategy', 'unknown')
        weight_msg = ""
        if strategy_name != 'unknown':
            weight_msg = self.update_weights(strategy_name, pnl_pct)

        # 0.1 Update Indicator Weights
        indicator_signals = entry_features.get('indicator_signals', {})
        if indicator_signals:
            self.update_indicator_weights(indicator_signals, pnl_pct)

        # 1. Update Global Stats
        stats = self.memory["global_stats"]
        stats["total_trades"] += 1
        if is_win:
            stats["wins"] += 1
        stats["win_rate"] = (stats["wins"] / stats["total_trades"]) * 100
        
        # 2. Update Coin Performance
        if symbol not in self.memory["coin_performance"]:
            self.memory["coin_performance"][symbol] = {
                "wins": 0, 
                "losses": 0, 
                "consecutive_losses": 0,
                "last_loss_time": 0
            }
            
        coin_stats = self.memory["coin_performance"][symbol]
        if is_win:
            coin_stats["wins"] += 1
            coin_stats["consecutive_losses"] = 0
        else:
            coin_stats["losses"] += 1
            coin_stats["consecutive_losses"] += 1
            coin_stats["last_loss_time"] = timestamp

        # 3. Add to History (Keep last 100)
        trade_record = {
            "symbol": symbol,
            "pnl": pnl_pct,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "timestamp": timestamp,
            "features": entry_features
        }
        self.memory["trade_history"].append(trade_record)
        if len(self.memory["trade_history"]) > 100:
            self.memory["trade_history"].pop(0)
            
        self._save_memory()
        return f"Brain updated: Global WR {stats['win_rate']:.1f}%, {symbol} Streak: {coin_stats['consecutive_losses']}L"

    def record_ghost_trade(self, symbol: str, entry_price: float, reason: str, signal_score: float):
        """
        Records a 'Filtered' signal as a virtual trade to track 'what if' performance.
        """
        # Avoid duplicate ghost trades for same symbol within short time
        for trade in self.memory.get("ghost_trades", []):
            if trade['symbol'] == symbol and (time.time() - trade['timestamp']) < 3600:
                return # Already tracking this symbol recently
        
        ghost_trade = {
            "symbol": symbol,
            "entry_price": entry_price,
            "reason": reason,
            "signal_score": signal_score,
            "timestamp": int(time.time()),
            "highest_price": entry_price,
            "status": "ACTIVE"
        }
        
        if "ghost_trades" not in self.memory:
            self.memory["ghost_trades"] = []
            
        self.memory["ghost_trades"].append(ghost_trade)
        self._save_memory()
        return f"👻 Ghost Trade Started: {symbol} @ {entry_price} (Filtered: {reason})"

    def update_ghost_trades(self, current_prices: Dict[str, float]):
        """
        Updates active ghost trades with latest market data.
        Checks if they would have hit TP/SL or expired.
        """
        active_trades = [t for t in self.memory.get("ghost_trades", []) if t['status'] == "ACTIVE"]
        if not active_trades:
            return

        updates_made = False
        current_time = int(time.time())
        
        # Simple Logic: 24h expiration, or TP +5%, SL -5%
        TP_PCT = 0.05
        SL_PCT = 0.05
        
        for trade in active_trades:
            symbol = trade['symbol']
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            entry_price = trade['entry_price']
            
            # Update Highest Price
            if current_price > trade['highest_price']:
                trade['highest_price'] = current_price
                updates_made = True
            
            # Calculate PnL
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Check Exit Conditions
            exit_reason = None
            final_pnl = 0.0
            
            # 1. Take Profit
            if pnl_pct >= (TP_PCT * 100):
                exit_reason = "TP_HIT"
                final_pnl = pnl_pct
                
            # 2. Stop Loss
            elif pnl_pct <= -(SL_PCT * 100):
                exit_reason = "SL_HIT"
                final_pnl = pnl_pct
                
            # 3. Time Expiration (24h)
            elif (current_time - trade['timestamp']) > (24 * 3600):
                exit_reason = "EXPIRED"
                final_pnl = pnl_pct
            
            if exit_reason:
                trade['status'] = "CLOSED"
                trade['exit_reason'] = exit_reason
                trade['exit_price'] = current_price
                trade['final_pnl'] = final_pnl
                trade['closed_at'] = current_time
                updates_made = True
                
        if updates_made:
            self._save_memory()

    def analyze_market_regime(self) -> Dict:
        """
        Analyze recent trade history to determine market regime.
        Returns: {
            "status": "BULL" | "BEAR" | "NEUTRAL" | "CRASH",
            "win_rate_24h": float,
            "avg_pnl_24h": float
        }
        """
        history = self.memory.get("trade_history", [])
        if not history:
            return {"status": "NEUTRAL", "win_rate_24h": 50.0, "avg_pnl_24h": 0.0}

        # Filter last 72h trades (Extended for 1H timeframe)
        current_time = int(time.time())
        lookback_period = 72 * 60 * 60 # 3 Days
        day_ago = current_time - lookback_period
        recent_trades = [t for t in history if t['timestamp'] > day_ago]
        
        if not recent_trades:
            return {"status": "NEUTRAL", "win_rate_24h": 50.0, "avg_pnl_24h": 0.0}

        wins = sum(1 for t in recent_trades if t['pnl'] > 0)
        total = len(recent_trades)
        win_rate = (wins / total) * 100
        avg_pnl = sum(t['pnl'] for t in recent_trades) / total
        
        # Determine Regime
        if avg_pnl < -5.0:
            status = "CRASH" # Severe losses
        elif win_rate > 60:
            status = "BULL"
        elif win_rate < 35:
            status = "BEAR"
        else:
            status = "NEUTRAL"
            
        return {"status": status, "win_rate_24h": win_rate, "avg_pnl_24h": avg_pnl}

    def analyze_winning_patterns(self) -> Dict:
        """
        Analyzes the features of winning trades to find the 'Sweet Spot'.
        """
        history = self.memory.get("trade_history", [])
        winning_trades = [t for t in history if t['pnl'] > 0]
        
        if len(winning_trades) < 5:
            return None # Not enough data yet
            
        # Calculate average features of winners
        avg_rsi = sum(t['features'].get('rsi', 50) for t in winning_trades) / len(winning_trades)
        avg_vol_ratio = sum(t['features'].get('volume_ratio', 1.0) for t in winning_trades) / len(winning_trades)
        
        return {
            "target_rsi": avg_rsi,
            "target_volume": avg_vol_ratio
        }

    def check_safety(self, symbol: str, current_volatility: float = 0, volume_ratio: float = 1.0, current_rsi: float = 50.0) -> Dict:
        """
        Advanced safety check with Market Regime, Volatility analysis AND Pattern Matching.
        """
        current_time = int(time.time())
        coin_stats = self.memory["coin_performance"].get(symbol, {})
        regime = self.analyze_market_regime()
        patterns = self.analyze_winning_patterns()
        
        # 1. Market Regime Safety Valve
        if regime['status'] == "CRASH":
            return {
                "safe": False,
                "reason": f"🛑 MARKET CRASH DETECTED (Avg PnL {regime['avg_pnl_24h']:.2f}%). HALTING.",
                "modifier": 0
            }
        
        # 2. Volatility Check (Skip if volatility is extreme in Bear market)
        if regime['status'] == "BEAR" and current_volatility > 5.0:
             return {
                "safe": False,
                "reason": f"🛑 Too volatile ({current_volatility:.1f}%) for Bear Market.",
                "modifier": 0
            }

        # 3. Volume Check (Avoid low volume pumps)
        # Lowered threshold to 0.2 to allow trades in quiet markets (especially for 1h timeframe)
        if volume_ratio < 0.2:
             return {
                "safe": False,
                "reason": f"⚠️ Volume too low (Ratio {volume_ratio:.2f}). Fake pump risk.",
                "modifier": 0
            }

        # 4. Consecutive Loss Cooldown
        consecutive_losses = coin_stats.get("consecutive_losses", 0)
        last_loss_time = coin_stats.get("last_loss_time", 0)
        
        if consecutive_losses >= 2:
            cooldown_period = 24 * 60 * 60  # 24 hours
            if current_time - last_loss_time < cooldown_period:
                remaining_hours = (cooldown_period - (current_time - last_loss_time)) / 3600
                return {
                    "safe": False, 
                    "reason": f"🛑 {symbol} is in penalty box (2 consecutive losses). Wait {remaining_hours:.1f}h",
                    "modifier": 0
                }
        
        # 5. Smart Modifiers based on Regime AND Patterns
        rsi_modifier = 0
        
        # Regime Base
        if regime['status'] == "BEAR":
            rsi_modifier = -5 # Be stricter
        elif regime['status'] == "BULL":
            rsi_modifier = 2  # Be more aggressive
            
        # Pattern Matching Bonus
        if patterns:
            # If current volume is similar to winning volume (within 20%)
            if volume_ratio > patterns['target_volume'] * 0.8:
                rsi_modifier += 2
                
            # If current RSI is close to winning RSI (within 5 points)
            if abs(current_rsi - patterns['target_rsi']) < 5:
                rsi_modifier += 1
            
        return {
            "safe": True, 
            "reason": f"✅ Safe (Regime: {regime['status']})", 
            "modifier": rsi_modifier
        }

    def get_dynamic_risk_adjustment(self, symbol: str) -> Dict:
        """
        Returns multipliers for Stop Loss and Take Profit based on Market Regime.
        """
        regime = self.analyze_market_regime()
        
        sl_multiplier = 1.0
        tp_multiplier = 1.0
        
        if regime['status'] == "BULL":
            # Boğa: Karı uzat (%50 daha fazla hedef), Stopu biraz gevşet (%20 tolerans)
            tp_multiplier = 1.5 
            sl_multiplier = 1.2 
        elif regime['status'] == "BEAR":
            # Ayı: Karı hemen al (%50 daha düşük hedef), Stopu sıkı tut (%20 daha sıkı)
            tp_multiplier = 0.5
            sl_multiplier = 0.8
        elif regime['status'] == "CRASH":
            # Çöküş: Panik satış modu
            tp_multiplier = 0.2
            sl_multiplier = 0.5
            
        return {
            "sl_multiplier": sl_multiplier,
            "tp_multiplier": tp_multiplier,
            "regime": regime['status']
        }
