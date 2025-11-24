# tests/test_core_logic.py
import pytest
import json
import time
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the functions we want to test
from demo.rpc_server import (
    handle_lock,
    handle_set_speed_limit,
    handle_get_config,
)
from demo.driver_behavior import compute_driver_behavior
from demo.config_store import get_effective_speed_limit, get_config_snapshot


# Mock the config store functions globally for RPC tests
@pytest.fixture(autouse=True)
def mock_config_store():
    # Patch the entire config_store module's functions
    with patch('demo.rpc_server.set_rpc_speed_limit') as mock_set, \
         patch('demo.rpc_server.get_config_snapshot') as mock_get_snapshot, \
         patch('demo.rpc_server.get_effective_speed_limit') as mock_get_effective:
        
        # Default mock return values
        mock_get_effective.return_value = 80.0
        mock_get_snapshot.return_value = {"current_zone": "City"}
        
        yield mock_set, mock_get_snapshot, mock_get_effective
