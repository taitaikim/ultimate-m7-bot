"""
M7 Core - Technical Filters
Advanced technical analysis filters including Support/Resistance detection.
"""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from typing import Dict, List, Optional, Any, Union

class SrVolumeFilter:
    """
    지지/저항선 및 볼륨 프로파일 기반 필터링 클래스
    
    Attributes:
        df (pd.DataFrame): 종가('Close')가 포함된 데이터프레임
        order (int): 극값 탐지 범위 (기본값: 5)
        support_levels (List[float]): 계산된 지지선 리스트
        resistance_levels (List[float]): 계산된 저항선 리스트
    """
    
    def __init__(self, df: pd.DataFrame, order: int = 5) -> None:
        """
        Args:
            df (pd.DataFrame): 주가 데이터 (반드시 'Close' 컬럼 포함)
            order (int): 지역 극값(Local Extrema) 탐색 범위
        """
        self.df = df
        self.order = order
        self.support_levels: List[float] = []
        self.resistance_levels: List[float] = []
        
        # 객체 생성과 동시에 레벨 계산 수행
        self._calculate_levels()
        
    def _calculate_levels(self) -> None:
        """
        내부 메서드: 지지선과 저항선을 계산하여 리스트에 저장
        **중요: 최근 120일(약 6개월) 데이터만 유효한 지지/저항선으로 인정**
        """
        if 'Close' not in self.df.columns or self.df.empty:
            return
            
        # 1. scipy를 이용한 극값 탐지
        # Local Minima (지지선 후보)
        support_idx = argrelextrema(
            self.df['Close'].values, 
            np.less, 
            order=self.order
        )[0]
        
        # Local Maxima (저항선 후보)
        resistance_idx = argrelextrema(
            self.df['Close'].values, 
            np.greater, 
            order=self.order
        )[0]
        
        # 2. 최근 데이터 필터링 (질문자님의 핵심 로직 유지!)
        # 데이터가 충분하다면 최근 120일(약 6개월) 이전의 지지선은 무시함
        data_len = len(self.df)
        cutoff_idx = data_len - 120 if data_len > 120 else 0
        
        self.support_levels = [
            float(self.df['Close'].iloc[i]) 
            for i in support_idx if i >= cutoff_idx
        ]
        
        self.resistance_levels = [
            float(self.df['Close'].iloc[i]) 
            for i in resistance_idx if i >= cutoff_idx
        ]
        
    def find_nearest_support(self, current_price: float) -> Optional[float]:
        """
        현재가 아래에 있는 가장 가까운 지지선을 찾습니다.
        """
        if not self.support_levels:
            return None

        # 현재가보다 낮은 지지선만 필터링
        valid_supports = [s for s in self.support_levels if s < current_price]
        
        if not valid_supports:
            return None
            
        # 그 중 가장 큰 값 (현재가와 가장 가까운 값) 반환
        return max(valid_supports)

    def check_support_proximity(
        self, 
        current_price: float, 
        threshold_pct: float = 3.0
    ) -> Dict[str, Any]:
        """
        5차 필터: 현재 주가가 지지선 근처에 있는지 확인
        
        Returns:
            Dict: {pass: bool, reason: str, ...}
        """
        nearest_support = self.find_nearest_support(current_price)
        
        if nearest_support is None:
            # 지지선이 없으면(신고가 영역 등) 통과로 간주하되 로그 남김
            return {
                'pass': True,
                'nearest_support': None,
                'distance_pct': 0.0,
                'reason': "지지선 없음 (신고가 영역/데이터 부족)"
            }
            
        distance_pct = ((current_price - nearest_support) / nearest_support) * 100
        
        if distance_pct <= threshold_pct:
            return {
                'pass': True,
                'nearest_support': nearest_support,
                'distance_pct': round(distance_pct, 2),
                'reason': f"지지선 근접 ({distance_pct:.1f}%)"
            }
        else:
            return {
                'pass': False,
                'nearest_support': nearest_support,
                'distance_pct': round(distance_pct, 2),
                'reason': f"지지선과 이격 과다 ({distance_pct:.1f}%)"
            }