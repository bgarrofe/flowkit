"""Tests for state persistence module."""

import json
from flowkit.state import StateManager, TaskCache


class TestStateManagerBasic:
    """Test basic StateManager functionality."""
    
    def test_state_manager_creation_memory(self):
        """Test creating in-memory state manager."""
        sm = StateManager()
        assert sm.storage_path is None
        assert sm.default_ttl is None
    
    def test_state_manager_creation_file(self, temp_dir):
        """Test creating file-based state manager."""
        storage_path = temp_dir / "state.json"
        sm = StateManager(storage_path=str(storage_path))
        assert sm.storage_path == storage_path
    
    def test_state_manager_with_ttl(self):
        """Test creating state manager with default TTL."""
        sm = StateManager(default_ttl=60.0)
        assert sm.default_ttl == 60.0


class TestStateManagerSetGet:
    """Test set and get operations."""
    
    def test_set_and_get(self):
        """Test basic set and get."""
        sm = StateManager()
        sm.set("key1", "value1")
        
        assert sm.get("key1") == "value1"
    
    def test_get_nonexistent(self):
        """Test getting nonexistent key."""
        sm = StateManager()
        assert sm.get("nonexistent") is None
    
    def test_get_with_default(self):
        """Test getting with default value."""
        sm = StateManager()
        assert sm.get("nonexistent", "default") == "default"
    
    def test_set_various_types(self):
        """Test setting various data types."""
        sm = StateManager()
        
        sm.set("string", "hello")
        sm.set("int", 42)
        sm.set("float", 3.14)
        sm.set("list", [1, 2, 3])
        sm.set("dict", {"a": 1, "b": 2})
        sm.set("bool", True)
        sm.set("none", None)
        
        assert sm.get("string") == "hello"
        assert sm.get("int") == 42
        assert sm.get("float") == 3.14
        assert sm.get("list") == [1, 2, 3]
        assert sm.get("dict") == {"a": 1, "b": 2}
        assert sm.get("bool") is True
        assert sm.get("none") is None
    
    def test_overwrite_value(self):
        """Test overwriting existing value."""
        sm = StateManager()
        sm.set("key", "value1")
        sm.set("key", "value2")
        
        assert sm.get("key") == "value2"


class TestStateManagerTTL:
    """Test TTL functionality."""
    
    def test_ttl_not_expired(self, mock_time):
        """Test value not expired within TTL."""
        sm = StateManager()
        sm.set("key", "value", ttl=10.0)
        
        # Advance time by 5 seconds (within TTL)
        mock_time.return_value = 1005.0
        
        assert sm.get("key") == "value"
    
    def test_ttl_expired(self, mock_time):
        """Test value expired after TTL."""
        sm = StateManager()
        sm.set("key", "value", ttl=10.0)
        
        # Advance time by 15 seconds (past TTL)
        mock_time.return_value = 1015.0
        
        assert sm.get("key") is None
    
    def test_default_ttl(self, mock_time):
        """Test using default TTL."""
        sm = StateManager(default_ttl=5.0)
        sm.set("key", "value")
        
        # Within TTL
        mock_time.return_value = 1003.0
        assert sm.get("key") == "value"
        
        # Past TTL
        mock_time.return_value = 1010.0
        assert sm.get("key") is None
    
    def test_no_ttl(self, mock_time):
        """Test value without TTL never expires."""
        sm = StateManager()
        sm.set("key", "value", ttl=None)
        
        # Advance time significantly
        mock_time.return_value = 2000.0
        
        assert sm.get("key") == "value"


class TestStateManagerHasDelete:
    """Test has and delete operations."""
    
    def test_has_existing(self):
        """Test has with existing key."""
        sm = StateManager()
        sm.set("key", "value")
        
        assert sm.has("key") is True
    
    def test_has_nonexistent(self):
        """Test has with nonexistent key."""
        sm = StateManager()
        assert sm.has("nonexistent") is False
    
    def test_has_expired(self, mock_time):
        """Test has with expired key."""
        sm = StateManager()
        sm.set("key", "value", ttl=10.0)
        
        mock_time.return_value = 1015.0
        assert sm.has("key") is False
    
    def test_delete_existing(self):
        """Test deleting existing key."""
        sm = StateManager()
        sm.set("key", "value")
        
        assert sm.delete("key") is True
        assert sm.get("key") is None
    
    def test_delete_nonexistent(self):
        """Test deleting nonexistent key."""
        sm = StateManager()
        assert sm.delete("nonexistent") is False


class TestStateManagerBulkOperations:
    """Test bulk operations."""
    
    def test_get_all(self):
        """Test getting all values."""
        sm = StateManager()
        sm.set("key1", "value1")
        sm.set("key2", "value2")
        sm.set("key3", "value3")
        
        all_values = sm.get_all()
        
        assert len(all_values) == 3
        assert all_values["key1"] == "value1"
        assert all_values["key2"] == "value2"
        assert all_values["key3"] == "value3"
    
    def test_get_all_excludes_expired(self, mock_time):
        """Test get_all excludes expired values."""
        sm = StateManager()
        sm.set("key1", "value1", ttl=10.0)
        sm.set("key2", "value2", ttl=20.0)
        sm.set("key3", "value3", ttl=None)
        
        # Expire key1
        mock_time.return_value = 1015.0
        
        all_values = sm.get_all()
        
        assert "key1" not in all_values
        assert all_values["key2"] == "value2"
        assert all_values["key3"] == "value3"
    
    def test_clear(self):
        """Test clearing all values."""
        sm = StateManager()
        sm.set("key1", "value1")
        sm.set("key2", "value2")
        
        sm.clear()
        
        assert sm.get("key1") is None
        assert sm.get("key2") is None
        assert sm.get_all() == {}
    
    def test_invalidate_expired(self, mock_time):
        """Test invalidating expired entries."""
        sm = StateManager()
        sm.set("key1", "value1", ttl=10.0)
        sm.set("key2", "value2", ttl=20.0)
        sm.set("key3", "value3", ttl=None)
        
        # Expire key1
        mock_time.return_value = 1015.0
        
        expired = sm.invalidate_expired()
        
        assert "key1" in expired
        assert len(expired) == 1
        assert sm.get("key1") is None
        assert sm.get("key2") == "value2"


class TestStateManagerMetadata:
    """Test metadata functionality."""
    
    def test_set_with_metadata(self):
        """Test setting value with metadata."""
        sm = StateManager()
        sm.set("key", "value", metadata={"source": "test", "version": 1})
        
        meta = sm.get_metadata("key")
        
        assert meta is not None
        assert meta["source"] == "test"
        assert meta["version"] == 1
    
    def test_get_metadata_includes_timestamp(self, mock_time):
        """Test metadata includes timestamp and age."""
        sm = StateManager()
        sm.set("key", "value")
        
        mock_time.return_value = 1005.0
        meta = sm.get_metadata("key")
        
        assert meta is not None
        assert meta["timestamp"] == 1000.0
        assert meta["age"] == 5.0
    
    def test_get_metadata_nonexistent(self):
        """Test getting metadata for nonexistent key."""
        sm = StateManager()
        assert sm.get_metadata("nonexistent") is None
    
    def test_get_metadata_expired(self, mock_time):
        """Test getting metadata for expired key."""
        sm = StateManager()
        sm.set("key", "value", ttl=10.0)
        
        mock_time.return_value = 1015.0
        assert sm.get_metadata("key") is None


class TestStateManagerPersistence:
    """Test file-based persistence."""
    
    def test_save_to_file(self, temp_dir):
        """Test saving state to file."""
        storage_path = temp_dir / "state.json"
        sm = StateManager(storage_path=str(storage_path))
        
        sm.set("key1", "value1")
        sm.set("key2", 42)
        
        # File should exist
        assert storage_path.exists()
        
        # File should contain valid JSON
        with open(storage_path) as f:
            data = json.load(f)
        
        assert "cache" in data
        assert "key1" in data["cache"]
        assert "key2" in data["cache"]
    
    def test_load_from_file(self, temp_dir):
        """Test loading state from file."""
        storage_path = temp_dir / "state.json"
        
        # Create first manager and save data
        sm1 = StateManager(storage_path=str(storage_path))
        sm1.set("key1", "value1")
        sm1.set("key2", [1, 2, 3])
        
        # Create second manager - should load existing data
        sm2 = StateManager(storage_path=str(storage_path))
        
        assert sm2.get("key1") == "value1"
        assert sm2.get("key2") == [1, 2, 3]
    
    def test_persistence_with_ttl(self, temp_dir, mock_time):
        """Test persistence respects TTL."""
        storage_path = temp_dir / "state.json"
        
        # Save with TTL
        sm1 = StateManager(storage_path=str(storage_path))
        sm1.set("key", "value", ttl=10.0)
        
        # Load after expiration
        mock_time.return_value = 1015.0
        sm2 = StateManager(storage_path=str(storage_path))
        
        assert sm2.get("key") is None
    
    def test_corrupted_file(self, temp_dir):
        """Test handling corrupted state file."""
        storage_path = temp_dir / "state.json"
        
        # Write corrupted JSON
        with open(storage_path, 'w') as f:
            f.write("{ invalid json }")
        
        # Should not crash, just start with empty cache
        sm = StateManager(storage_path=str(storage_path))
        assert sm.get_all() == {}
    
    def test_delete_persists(self, temp_dir):
        """Test that delete operation persists to file."""
        storage_path = temp_dir / "state.json"
        
        sm1 = StateManager(storage_path=str(storage_path))
        sm1.set("key1", "value1")
        sm1.set("key2", "value2")
        sm1.delete("key1")
        
        sm2 = StateManager(storage_path=str(storage_path))
        assert sm2.get("key1") is None
        assert sm2.get("key2") == "value2"
    
    def test_clear_persists(self, temp_dir):
        """Test that clear operation persists to file."""
        storage_path = temp_dir / "state.json"
        
        sm1 = StateManager(storage_path=str(storage_path))
        sm1.set("key1", "value1")
        sm1.clear()
        
        sm2 = StateManager(storage_path=str(storage_path))
        assert sm2.get_all() == {}


class TestTaskCache:
    """Test TaskCache decorator."""
    
    def test_cache_basic(self):
        """Test basic caching functionality."""
        sm = StateManager()
        cache = TaskCache(sm)
        
        call_count = 0
        
        @cache
        def expensive_function():
            nonlocal call_count
            call_count += 1
            return "result"
        
        # First call - should execute
        result1 = expensive_function()
        assert result1 == "result"
        assert call_count == 1
        
        # Second call - should use cache
        result2 = expensive_function()
        assert result2 == "result"
        assert call_count == 1  # Not incremented
    
    def test_cache_with_ttl(self, mock_time):
        """Test caching with TTL."""
        sm = StateManager()
        cache = TaskCache(sm, ttl=10.0)
        
        call_count = 0
        
        @cache
        def my_function():
            nonlocal call_count
            call_count += 1
            return "result"
        
        # First call
        my_function()
        assert call_count == 1
        
        # Within TTL - should use cache
        mock_time.return_value = 1005.0
        my_function()
        assert call_count == 1
        
        # After TTL - should execute again
        mock_time.return_value = 1015.0
        my_function()
        assert call_count == 2
    
    def test_cache_different_functions(self):
        """Test caching different functions."""
        sm = StateManager()
        cache = TaskCache(sm)
        
        @cache
        def func1():
            return "result1"
        
        @cache
        def func2():
            return "result2"
        
        assert func1() == "result1"
        assert func2() == "result2"
        
        # Both should be cached separately
        assert sm.get("func1") == "result1"
        assert sm.get("func2") == "result2"


class TestStateManagerRepr:
    """Test StateManager string representation."""
    
    def test_repr_memory(self):
        """Test repr for in-memory state manager."""
        sm = StateManager()
        sm.set("key1", "value1")
        sm.set("key2", "value2")
        
        repr_str = repr(sm)
        
        assert "in-memory" in repr_str
        assert "cached_items=2" in repr_str
    
    def test_repr_file(self, temp_dir):
        """Test repr for file-based state manager."""
        storage_path = temp_dir / "state.json"
        sm = StateManager(storage_path=str(storage_path))
        sm.set("key", "value")
        
        repr_str = repr(sm)
        
        assert "state.json" in repr_str
        assert "cached_items=1" in repr_str


class TestStateManagerEdgeCases:
    """Test edge cases."""
    
    def test_empty_key(self):
        """Test with empty string key."""
        sm = StateManager()
        sm.set("", "value")
        
        assert sm.get("") == "value"
    
    def test_none_value(self):
        """Test storing None value."""
        sm = StateManager()
        sm.set("key", None)
        
        # None is a valid value, different from missing key
        assert sm.has("key") is True
        assert sm.get("key") is None
    
    def test_zero_ttl(self, mock_time):
        """Test with zero TTL (immediate expiration)."""
        sm = StateManager()
        sm.set("key", "value", ttl=0.0)
        
        # Even tiny time advance should expire it
        mock_time.return_value = 1000.1
        assert sm.get("key") is None
    
    def test_negative_ttl(self, mock_time):
        """Test with negative TTL."""
        sm = StateManager()
        sm.set("key", "value", ttl=-1.0)
        
        # Should be immediately expired
        assert sm.get("key") is None
    
    def test_large_value(self):
        """Test storing large value."""
        sm = StateManager()
        large_list = list(range(10000))
        sm.set("large", large_list)
        
        assert sm.get("large") == large_list

