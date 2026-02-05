import time
from typing import Callable, Any
from functools import wraps

class CircuitBreaker:
    """API hataları için devre kesici pattern"""
    def __init__(self, failure_threshold: int = 5, timeout: int = 60, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return False
            return True
        return False
    
    def on_success(self):
        self.failures = 0
        self.state = "CLOSED"
    
    def on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.is_open():
            raise Exception(f"Circuit breaker OPEN - API çağrısı engellendi. {self.recovery_timeout}s sonra tekrar denenecek.")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

# Decorator versiyonu
def circuit_breaker(failure_threshold=5, timeout=60):
    breaker = CircuitBreaker(failure_threshold, timeout)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
