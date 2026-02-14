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
    CONSENSUS_THRESHOLD: float = 0.60 # Voting Consensus Threshold (0.60 = 60%)
    FUNDING_Z_SCORE_THRESHOLD: float = 2.0
    ARBITRAGE_SPREAD_THRESHOLD: float = 0.01  # 1%
    
    # Risk
    MAX_POSITION_SIZE_USD: float = 1.0  # Deprecated in favor of PCT
    MAX_POSITION_PCT: float = 20.0 # %20 of portfolio per trade
    MAX_OPEN_POSITIONS: int = 10    # Maximum 10 open positions (was 4)
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
    LOG_FILE: str = "data/bot_activity_paper.log"
    
    # Alerting
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Sentiment Analysis APIs
    TWITTER_API_KEY: Optional[str] = None # Bearer Token
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: Optional[str] = "kripto-bot/1.0"

    # Emergency & Limits
    MAX_DAILY_LOSS_PCT: float = 50.0  # Günlük maksimum %50 zarar (User request: 50 dolar limit -> high percentage)
    EMERGENCY_SHUTDOWN_ENABLED: bool = True
    
    # Sniper Mode Risk
    SNIPER_MAX_RISK_PCT: float = 98.0 # %98 of free balance for All-In

    # Dev Mode
    USE_MOCK_DATA: bool = True  # Default to True for safe local paper runs
    LIVE_TRADING: bool = False   # Set to True to enable real orders
    PAPER_TRADING_BALANCE: float = 10000.0 # Virtual balance (USDT) for paper trading
    SLEEP_INTERVAL: int = 10    # Sleep time between scans in seconds
    
    # Feature Flags
    SENTIMENT_ENABLED: bool = False
    DISABLE_SENTIMENT_ANALYSIS: bool = True
    
    # --- FREQTRADE INSPIRED FEATURES ---
    
    # 1. Dynamic ROI (Time-Based Take Profit)
    # Format: {minutes: profit_pct}
    # Example: {0: 10.0, 30: 5.0, 60: 2.0, 120: 1.0}
    # 0-30 min: Aim for 10%
    # 30-60 min: Aim for 5%
    # 60-120 min: Aim for 2%
    # >120 min: Aim for 1% (Just get out with profit)
    DYNAMIC_ROI_ENABLED: bool = True
    DYNAMIC_ROI_TABLE: dict = {
        0: 10.0,   # İlk 30 dk hedef %10 (Pump yakalama)
        30: 5.0,   # 30. dk'dan sonra hedef %5'e düşer
        60: 3.0,   # 1 saatten sonra hedef %3'e düşer
        120: 1.5,  # 2 saatten sonra hedef %1.5 (Parayı kurtar)
        240: 0.5   # 4 saatten sonra %0.5 kârla çık (Zaman maliyeti)
    }
    
    # 2. Cooldown Mechanism
    COOLDOWN_ENABLED: bool = True
    COOLDOWN_MINUTES_AFTER_LOSS: int = 120 # Zarar eden coine 2 saat girme
    COOLDOWN_MINUTES_AFTER_WIN: int = 30   # Kâr eden coine 30 dk girme (Dinlen)
    
    # 3. Edge Calculation (Win Rate Filter)
    EDGE_FILTER_ENABLED: bool = True
    MIN_WIN_RATE_FOR_ENTRY: float = 35.0   # %35'in altında kazanma oranı varsa girme (Bear markette esnek)
    MIN_TRADES_FOR_EDGE: int = 5           # En az 5 işlemden sonra karar ver
    
    # 4. Stoploss Guard (Rolling Window)
    STOPLOSS_GUARD_ENABLED: bool = True
    SL_GUARD_WINDOW_MINUTES: int = 60      # Son 60 dakikada
    SL_GUARD_MAX_SL_HITS: int = 2          # En fazla 2 stop-loss
    SL_GUARD_BLOCK_MESSAGE: str = "🛡️ SL GUARD: Çok fazla stop (%d/%d) son %d dk. Bekle %s"
    
    # 5. Idempotent Orders & Retry
    IDEMPOTENT_ORDERS_ENABLED: bool = True
    ORDER_RETRY_MAX: int = 3
    ORDER_RETRY_BASE_MS: int = 300         # Exponential backoff tabanı (ms)
    
    # 6. Step Trailing (Basamaklı Trailing Stop)
    TRAILING_STEP_ENABLED: bool = True
    TRAILING_STEP_PCT: float = 0.8         # Fiyat, son zirveyi en az %0.8 aşınca stop yukarı taşınır
    
    # Opportunity Manager
    OPP_MIN_HOLD_SECONDS: int = 3600       # En az 1 saat elde tut
    OPP_LOCK_BREAK_DIFF: float = 20.0      # Kilidi kırmak için gereken skor farkı

    class Config:
        env_file = ".env"

settings = Settings()
