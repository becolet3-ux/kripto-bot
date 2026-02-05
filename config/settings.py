from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API Keys
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    
    # Bot Parameters
    # Trading Pairs (Binance TR uses _TRY pairs)
    SYMBOLS: List[str] = [
        'BTC_TRY',
        'ETH_TRY',
        'SOL_TRY',
        'AVAX_TRY',
        'PEPE_TRY'
    ]

    # Timeframe for analysis
    TIMEFRAME: str = '1h'
    EXCHANGES: List[str] = ["binance", "bybit"]
    
    # Mode
    TRADING_MODE: str = 'spot' # 'spot' or 'futures'
    IS_TR_BINANCE: bool = False # Overridden by env

    # Futures Settings
    LEVERAGE: int = 1
    MARGIN_TYPE: str = 'ISOLATED' # 'ISOLATED' or 'CROSS'

    # Thresholds
    FUNDING_Z_SCORE_THRESHOLD: float = 2.0
    ARBITRAGE_SPREAD_THRESHOLD: float = 0.01  # 1%
    
    # Risk
    MAX_POSITION_SIZE_USD: float = 1.0  # Deprecated in favor of PCT
    MAX_POSITION_PCT: float = 20.0 # %20 of portfolio per trade
    STOP_LOSS_PCT: float = 5.0   # %5 Stop Loss
    TAKE_PROFIT_PCT: float = 10.0 # %10 Take Profit
    
    # Advanced Risk
    TRAILING_STOP_PCT: float = 2.0 # %2 Trailing Stop (Activates after profit)
    DCA_ENABLED: bool = True
    DCA_MAX_STEPS: int = 2
    DCA_STEP_SCALE: float = 1.5 # Multiplier for next DCA step amount
    DCA_DROP_THRESHOLD: float = 3.0 # %3 Drop to trigger DCA
    
    # Files
    EMERGENCY_STOP_FILE: str = "data/emergency_stop.flag"
    
    # Alerting
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Sentiment Analysis APIs
    TWITTER_API_KEY: Optional[str] = None # Bearer Token
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: Optional[str] = "kripto-bot/1.0"

    # Emergency & Limits
    MAX_DAILY_LOSS_PCT: float = 5.0  # Günlük maksimum %5 zarar
    EMERGENCY_SHUTDOWN_ENABLED: bool = True

    # Dev Mode
    USE_MOCK_DATA: bool = False # Set to False to use real API
    LIVE_TRADING: bool = True   # Set to True to enable real orders
    SLEEP_INTERVAL: int = 10    # Sleep time between scans in seconds

    class Config:
        env_file = ".env"

settings = Settings()
