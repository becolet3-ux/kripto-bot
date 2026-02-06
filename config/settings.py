from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API Keys
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    
    # Bot Parameters
    # Trading Pairs (Global uses /USDT pairs)
    SYMBOLS: List[str] = [
        'BTC/USDT',
        'ETH/USDT',
        'SOL/USDT',
        'AVAX/USDT',
        'PEPE/USDT'
    ]

    # Timeframe for analysis
    TIMEFRAME: str = '1h'
    EXCHANGES: List[str] = ["binance", "bybit"]
    
    # Mode
    TRADING_MODE: str = 'spot' # 'spot' or 'futures'
    IS_TR_BINANCE: bool = False # Set to False for Global

    # Futures Settings
    LEVERAGE: int = 1
    MARGIN_TYPE: str = 'ISOLATED' # 'ISOLATED' or 'CROSS'

    # Thresholds
    FUNDING_Z_SCORE_THRESHOLD: float = 2.0
    ARBITRAGE_SPREAD_THRESHOLD: float = 0.01  # 1%
    
    # Risk
    MAX_POSITION_SIZE_USD: float = 1.0  # Deprecated in favor of PCT
    MAX_POSITION_PCT: float = 20.0 # %20 of portfolio per trade
    MAX_OPEN_POSITIONS: int = 4    # Maximum 4 open positions
    STOP_LOSS_PCT: float = 5.0   # %5 Stop Loss
    TAKE_PROFIT_PCT: float = 10.0 # %10 Take Profit
    
    # Advanced Risk (Phase 1)
    TRAILING_STOP_ATR_MULTIPLIER: float = 2.0
    PARTIAL_TAKE_PROFIT_PCT: float = 4.0  # %4 Profit -> Take 50%
    PARTIAL_EXIT_RATIO: float = 0.5       # Close 50%
    TRAILING_STOP_TIGHT_MULTIPLIER: float = 1.5 # After partial exit
    TIME_BASED_EXIT_HOURS: int = 24
    MAX_HOLD_TIME_HOURS: int = 48
    
    # Advanced Risk (Phase 2 - Volatility Sizing)
    VOLATILITY_LOW_THRESHOLD: float = 2.0   # <%2 Low
    VOLATILITY_HIGH_THRESHOLD: float = 4.0  # >%4 High
    
    POS_SIZE_LOW_VOL_PCT: float = 35.0      # %35 Portfolio for Low Vol
    POS_SIZE_MED_VOL_PCT: float = 25.0      # %25 Portfolio for Med Vol
    POS_SIZE_HIGH_VOL_PCT: float = 15.0     # %15 Portfolio for High Vol
    
    LEVERAGE_LOW_VOL: int = 3
    LEVERAGE_MED_VOL: int = 2
    LEVERAGE_HIGH_VOL: int = 1
    
    TRAILING_STOP_PCT: float = 2.0 # Legacy fixed % trailing stop
    DCA_ENABLED: bool = True
    DCA_MAX_STEPS: int = 2
    DCA_STEP_SCALE: float = 1.5 # Multiplier for next DCA step amount
    DCA_DROP_THRESHOLD: float = 3.0 # %3 Drop to trigger DCA
    
    # Files
    EMERGENCY_STOP_FILE: str = "data/emergency_stop.flag"
    STATE_FILE: str = "data/bot_state.json"
    STATS_FILE: str = "data/bot_stats.json"
    LOG_FILE: str = "data/bot_activity.log"
    
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
    LIVE_TRADING: bool = False   # Set to True to enable real orders
    PAPER_TRADING_BALANCE: float = 10000.0 # Virtual balance (USDT) for paper trading
    SLEEP_INTERVAL: int = 10    # Sleep time between scans in seconds
    
    # Feature Flags
    SENTIMENT_ENABLED: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
