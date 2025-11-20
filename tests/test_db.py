import pytest
import sys
import os

# Add project root to sys.path to allow importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from m7_cloud.db_manager import DBManager

def test_db_manager_singleton():
    """Test DBManager initialization with mocked env vars"""
    with patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'}):
        with patch('m7_cloud.db_manager.create_client') as mock_create:
            db = DBManager()
            assert db.url == 'https://test.supabase.co'
            mock_create.assert_called_once()

def test_sanitize_val():
    """Test the internal sanitization logic via log_signal"""
    with patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'}):
        with patch('m7_cloud.db_manager.create_client') as mock_create:
            # Setup mock client
            mock_supabase = MagicMock()
            mock_create.return_value = mock_supabase
            
            db = DBManager()
            
            # Test Case: NaN value
            filters = {'test': 'pass'}
            db.log_signal('TEST', 'BUY', float('nan'), filters)
            
            # Verify insert called with 0.0 or None, NOT NaN
            # We need to check the arguments passed to insert
            args, _ = mock_supabase.table().insert.call_args
            inserted_data = args[0]
            
            assert inserted_data['entry_price'] == 0.0
            assert inserted_data['ticker'] == 'TEST'
