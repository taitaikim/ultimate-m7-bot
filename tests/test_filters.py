import pytest
import pandas as pd
import numpy as np
from m7_core.filters import SrVolumeFilter

def test_sr_filter_initialization(sample_stock_data):
    """Test if SrVolumeFilter initializes correctly"""
    sr_filter = SrVolumeFilter(sample_stock_data, order=5)
    assert sr_filter.df is not None
    assert sr_filter.order == 5
    assert len(sr_filter.support_levels) >= 0
    assert len(sr_filter.resistance_levels) >= 0

def test_find_nearest_support(sample_stock_data):
    """Test finding the nearest support level"""
    sr_filter = SrVolumeFilter(sample_stock_data)
    
    # Manually set support levels for predictable testing
    sr_filter.support_levels = [100.0, 110.0, 120.0]
    
    # Case 1: Price above all supports
    nearest = sr_filter.find_nearest_support(125.0)
    assert nearest == 120.0
    
    # Case 2: Price between supports
    nearest = sr_filter.find_nearest_support(115.0)
    assert nearest == 110.0
    
    # Case 3: Price below all supports
    nearest = sr_filter.find_nearest_support(90.0)
    assert nearest is None

def test_check_support_proximity(sample_stock_data):
    """Test the 5th layer filter logic"""
    sr_filter = SrVolumeFilter(sample_stock_data)
    sr_filter.support_levels = [100.0]
    
    # Case 1: Within 3% (Pass)
    # 102 is 2% above 100
    result = sr_filter.check_support_proximity(102.0, threshold_pct=3.0)
    assert result['pass'] is True
    assert "지지선 근접" in result['reason']
    
    # Case 2: Outside 3% (Fail)
    # 110 is 10% above 100
    result = sr_filter.check_support_proximity(110.0, threshold_pct=3.0)
    assert result['pass'] is False
    assert "이격 과다" in result['reason']
