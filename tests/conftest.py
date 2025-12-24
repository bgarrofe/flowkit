"""Pytest configuration and fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from flowkit.task import Task
from flowkit.state import StateManager


@pytest.fixture(autouse=True)
def clear_task_registry():
    """Clear the task registry before and after each test."""
    Task.clear_registry()
    yield
    Task.clear_registry()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def state_manager(temp_dir):
    """Create a StateManager with temporary file storage."""
    storage_path = temp_dir / "state.json"
    return StateManager(storage_path=str(storage_path))


@pytest.fixture
def mock_sleep(mocker):
    """Mock time.sleep to speed up retry tests."""
    return mocker.patch('time.sleep')


@pytest.fixture
def mock_time(mocker):
    """Mock time.time for consistent timing tests."""
    mock = mocker.patch('time.time')
    mock.return_value = 1000.0
    return mock

