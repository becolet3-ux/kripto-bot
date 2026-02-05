import traceback
import functools
import time
import requests
from typing import Callable, Any
from enum import Enum

class ErrorSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ErrorHandler:
    """Merkezi hata yönetimi"""
    
    def __init__(self, telegram_notifier=None, logger=None):
        self.telegram = telegram_notifier
        self.logger = logger
        self.error_counts = {}
    
    def handle_error(self, error: Exception, context: str, severity: ErrorSeverity):
        """Hataları kategorize et ve yönet"""
        error_type = type(error).__name__
        error_msg = str(error)
        stack_trace = traceback.format_exc()
        
        # Hata sayısını artır
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Loglama
        log_msg = f"{context} - {error_type}: {error_msg}"
        
        if self.logger:
            if severity == ErrorSeverity.CRITICAL:
                self.logger.critical(log_msg + f"\n{stack_trace}")
                if self.telegram:
                    self.telegram.send_alert(f"🔴 CRITICAL ERROR\n{context}\n{error_msg}")
            elif severity == ErrorSeverity.HIGH:
                self.logger.error(log_msg)
                if self.telegram and self.error_counts[error_type] >= 3:
                    self.telegram.send_alert(f"⚠️ Recurring Error\n{error_type} (x{self.error_counts[error_type]})\n{context}")
            elif severity == ErrorSeverity.MEDIUM:
                self.logger.warning(log_msg)
            else:
                self.logger.info(log_msg)
        else:
            print(f"[{severity.value}] {log_msg}")
    
    def safe_execute(self, func: Callable, *args, context: str = "", severity: ErrorSeverity = ErrorSeverity.MEDIUM, **kwargs) -> Any:
        """Fonksiyonu güvenli şekilde çalıştır"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, context, severity)
            return None

# Singleton instance (will be initialized in main)
error_handler = ErrorHandler()

# Decorator versiyonu
def safe_api_call(context: str = "", severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Use the global instance or create a temporary one if not ready
                handler = error_handler
                handler.handle_error(e, context or func.__name__, severity)
                return None
        return wrapper
    return decorator

# Ağ bağlantısı kopması için özel handler
class NetworkErrorHandler:
    """Ağ hatalarına özel retry mekanizması"""
    
    @staticmethod
    def retry_on_network_error(max_retries: int = 3, delay: int = 5, logger=None):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except (ConnectionError, TimeoutError, requests.exceptions.RequestException) as e:
                        last_exception = e
                        if logger:
                            logger.warning(f"Network error on attempt {attempt + 1}/{max_retries}: {e}")
                        
                        if attempt < max_retries - 1:
                            time.sleep(delay * (attempt + 1))  # Exponential backoff
                        else:
                            # Son deneme de başarısız oldu
                            pass # Let it raise or handle
                
                raise last_exception
            return wrapper
        return decorator
