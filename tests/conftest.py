import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def sample_stock_data():
    """Creates a sample DataFrame for testing"""
    dates = pd.date_range(start='2023-01-01', periods=100)
    data = {
        'Close': np.random.normal(100, 10, 100).cumsum() + 100,
        'Volume': np.random.randint(1000, 10000, 100)
    }
    df = pd.DataFrame(data, index=dates)
    return df

@pytest.fixture
def mock_market_data():
    """Creates mock market data (QQQ, TNX)"""
    dates = pd.date_range(start='2023-01-01', periods=150)
    
    # Create MultiIndex columns for yfinance structure
    iterables = [['QQQ', '^TNX'], ['Close', 'Volume']]
    index = pd.MultiIndex.from_product(iterables, names=['Ticker', 'Price'])
    
    df = pd.DataFrame(np.random.randn(150, 4), index=dates, columns=index)
    
    # Make realistic values
    df[('QQQ', 'Close')] = 300.0  # Flat trend
    df[('^TNX', 'Close')] = 4.0   # Flat rate
    
    return df
