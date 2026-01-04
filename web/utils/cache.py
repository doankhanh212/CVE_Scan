# web/utils/cache.py
"""
Simple in-memory cache with TTL for scan statistics
Giảm tải cho API bằng cách cache kết quả tính toán
"""

import time
import threading
from typing import Any, Optional


class SimpleCache:
    """Thread-safe cache with TTL"""
    
    def __init__(self, ttl_seconds: int = 5):
        self.cache = {}
        self.lock = threading.Lock()
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        with self.lock:
            if key not in self.cache:
                return None
            
            value, timestamp = self.cache[key]
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                return None
            
            return value
    
    def set(self, key: str, value: Any):
        """Set cache value with current timestamp"""
        with self.lock:
            self.cache[key] = (value, time.time())
    
    def delete(self, key: str):
        """Delete cache entry"""
        with self.lock:
            self.cache.pop(key, None)
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
    
    def cleanup(self):
        """Remove expired entries"""
        with self.lock:
            now = time.time()
            expired = [k for k, (_, ts) in self.cache.items() if now - ts > self.ttl]
            for key in expired:
                del self.cache[key]


# Global cache instances
stats_cache = SimpleCache(ttl_seconds=5)  # Cache scan stats for 5s
list_cache = SimpleCache(ttl_seconds=3)   # Cache list for 3s
