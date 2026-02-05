import time
from collections import deque
from threading import Lock

import asyncio

class RateLimiter:
    """Token bucket algoritması ile rate limiting"""
    def __init__(self, max_requests: int = 1200, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()
    
    def allow_request(self) -> bool:
        with self.lock:
            current_time = time.time()
            
            # Zaman penceresi dışındaki istekleri temizle
            while self.requests and self.requests[0] < current_time - self.time_window:
                self.requests.popleft()
            
            if len(self.requests) < self.max_requests:
                self.requests.append(current_time)
                return True
            return False
    
    async def wait_if_needed(self):
        """Gerekirse bekle"""
        while not self.allow_request():
            await asyncio.sleep(0.1)
