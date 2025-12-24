"""State persistence and caching module for flowkit workflows."""

import json
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta

from .logging import get_logger, LogLevel


class StateManager:
    """
    Manages task result caching and state persistence.
    
    Supports both in-memory and file-based persistence. Can be used to
    cache task results and resume failed DAG runs from the last successful task.
    
    Attributes:
        storage_path: Optional path for file-based persistence
        default_ttl: Default time-to-live for cached results in seconds
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        default_ttl: Optional[float] = None,
    ):
        """
        Initialize a StateManager.
        
        Args:
            storage_path: Optional path for file-based persistence.
                         If None, uses in-memory storage only (default: None)
            default_ttl: Default time-to-live for cached results in seconds.
                        If None, results never expire (default: None)
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger()
        
        # Load existing state from file if path is provided
        if self.storage_path and self.storage_path.exists():
            self._load_from_file()
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store a value in the state manager.
        
        Args:
            key: Unique key for the value (typically task name)
            value: Value to store (must be JSON-serializable for file persistence)
            ttl: Time-to-live in seconds. If None, uses default_ttl (default: None)
            metadata: Optional metadata to store with the value (default: None)
        """
        ttl_to_use = ttl if ttl is not None else self.default_ttl
        
        entry = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl_to_use,
            "metadata": metadata or {},
        }
        
        self._cache[key] = entry
        
        # Persist to file if storage path is configured
        if self.storage_path:
            self._save_to_file()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from the state manager.
        
        Args:
            key: Key to retrieve
            default: Default value if key not found or expired (default: None)
        
        Returns:
            The stored value, or default if not found or expired
        """
        if key not in self._cache:
            return default
        
        entry = self._cache[key]
        
        # Check if entry has expired
        if entry["ttl"] is not None:
            age = time.time() - entry["timestamp"]
            if age > entry["ttl"]:
                # Entry expired, remove it
                del self._cache[key]
                if self.storage_path:
                    self._save_to_file()
                return default
        
        return entry["value"]
    
    def has(self, key: str) -> bool:
        """
        Check if a key exists and is not expired.
        
        Args:
            key: Key to check
        
        Returns:
            True if key exists and is not expired, False otherwise
        """
        return self.get(key) is not None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the state manager.
        
        Args:
            key: Key to delete
        
        Returns:
            True if key was deleted, False if key didn't exist
        """
        if key in self._cache:
            del self._cache[key]
            if self.storage_path:
                self._save_to_file()
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        if self.storage_path:
            self._save_to_file()
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all non-expired values.
        
        Returns:
            Dictionary of all non-expired key-value pairs
        """
        result = {}
        expired_keys = []
        
        for key, entry in self._cache.items():
            # Check expiration
            if entry["ttl"] is not None:
                age = time.time() - entry["timestamp"]
                if age > entry["ttl"]:
                    expired_keys.append(key)
                    continue
            
            result[key] = entry["value"]
        
        # Clean up expired entries
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys and self.storage_path:
            self._save_to_file()
        
        return result
    
    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a key.
        
        Args:
            key: Key to get metadata for
        
        Returns:
            Metadata dictionary, or None if key doesn't exist
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        if entry["ttl"] is not None:
            age = time.time() - entry["timestamp"]
            if age > entry["ttl"]:
                return None
        
        return {
            "timestamp": entry["timestamp"],
            "ttl": entry["ttl"],
            "age": time.time() - entry["timestamp"],
            **entry["metadata"],
        }
    
    def invalidate_expired(self) -> List[str]:
        """
        Remove all expired entries.
        
        Returns:
            List of keys that were invalidated
        """
        expired_keys = []
        
        for key, entry in list(self._cache.items()):
            if entry["ttl"] is not None:
                age = time.time() - entry["timestamp"]
                if age > entry["ttl"]:
                    expired_keys.append(key)
                    del self._cache[key]
        
        if expired_keys and self.storage_path:
            self._save_to_file()
        
        return expired_keys
    
    def _save_to_file(self) -> None:
        """Save cache to file."""
        if not self.storage_path:
            return
        
        # Ensure parent directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert cache to JSON-serializable format
        data = {
            "version": "1.0",
            "saved_at": datetime.utcnow().isoformat(),
            "cache": self._cache,
        }
        
        # Write to file
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _load_from_file(self) -> None:
        """Load cache from file."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Load cache and invalidate expired entries
            self._cache = data.get("cache", {})
            self.invalidate_expired()
        except (json.JSONDecodeError, KeyError) as e:
            # If file is corrupted, start with empty cache
            self.logger._log(LogLevel.WARNING, f"Could not load state from {self.storage_path}: {e}")
            self._cache = {}
    
    def __repr__(self) -> str:
        """String representation of the state manager."""
        cache_size = len(self._cache)
        storage = str(self.storage_path) if self.storage_path else "in-memory"
        return f"StateManager(storage={storage}, cached_items={cache_size})"


class TaskCache:
    """
    Decorator-based caching for tasks.
    
    Wraps task functions to automatically cache their results using a StateManager.
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        ttl: Optional[float] = None,
        cache_key_func: Optional[callable] = None,
    ):
        """
        Initialize a TaskCache.
        
        Args:
            state_manager: StateManager instance to use for caching
            ttl: Time-to-live for cached results in seconds (default: None)
            cache_key_func: Optional function to generate cache keys from
                           task arguments. If None, uses task name only.
        """
        self.state_manager = state_manager
        self.ttl = ttl
        self.cache_key_func = cache_key_func
        self.logger = get_logger()
    
    def __call__(self, func: callable) -> callable:
        """
        Wrap a function with caching.
        
        Args:
            func: Function to wrap
        
        Returns:
            Wrapped function with caching
        """
        def wrapper(*args, **kwargs):
            # Generate cache key
            if self.cache_key_func:
                cache_key = self.cache_key_func(func, *args, **kwargs)
            else:
                cache_key = func.__name__
            
            # Check cache
            cached_value = self.state_manager.get(cache_key)
            if cached_value is not None:
                self.logger._log(LogLevel.INFO, f"Cache hit for {cache_key}")
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            self.state_manager.set(
                cache_key,
                result,
                ttl=self.ttl,
                metadata={"function": func.__name__},
            )
            
            return result
        
        return wrapper

