class BotError(Exception):
    """Base exception for all bot related errors"""
    pass

class NetworkError(BotError):
    """Raised when there is a network/connection issue"""
    pass

class ExchangeError(BotError):
    """Raised when the exchange returns an error"""
    pass

class InsufficientBalanceError(BotError):
    """Raised when there is not enough balance to perform an operation"""
    pass

class ConfigurationError(BotError):
    """Raised when there is a configuration error"""
    pass

class DataError(BotError):
    """Raised when there is an issue with data fetching or processing"""
    pass
