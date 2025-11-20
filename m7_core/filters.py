import pandas as pd
import numpy as np
from scipy.signal import argrelextrema


class SrVolumeFilter:
    """
    지지/저항선 및 볼륨 프로파일 기반 필터
    Scipy를 사용한 Local Extrema 분석
    """
    
    def __init__(self, df, order=5):
        """
        Args:
            df: 가격 데이터프레임 (Close 컬럼 필요)
            order: 극값 탐지 범위 (기본 5일)
        """
        self.df = df
        self.order = order
        self.support_levels = []
        self.resistance_levels = []
        
    def calculate_support_resistance(self):
        """
        지지선/저항선 계산 (Local Extrema 방식)
        
        Returns:
            dict: {'support': [prices], 'resistance': [prices]}
        """
        try:
            # Local minima (지지선)
            local_min_idx = argrelextrema(self.df['Close'].values, np.less, order=self.order)[0]
            support_levels = self.df['Close'].iloc[local_min_idx].values
            
            # Local maxima (저항선)
            local_max_idx = argrelextrema(self.df['Close'].values, np.greater, order=self.order)[0]
            resistance_levels = self.df['Close'].iloc[local_max_idx].values
            
            # 최근 6개월 데이터만 사용 (더 관련성 높음)
            recent_cutoff = len(self.df) - 120  # 약 6개월
            self.support_levels = [s for i, s in zip(local_min_idx, support_levels) if i > recent_cutoff]
            self.resistance_levels = [r for i, r in zip(local_max_idx, resistance_levels) if i > recent_cutoff]
            
            return {
                'support': sorted(self.support_levels),
                'resistance': sorted(self.resistance_levels, reverse=True)
            }
        except Exception as e:
            print(f"  ⚠️ 지지/저항선 계산 실패: {e}")
            return {'support': [], 'resistance': []}
    
    def find_nearest_support(self, current_price):
        """
        현재가 아래의 가장 가까운 지지선 찾기
        
        Args:
            current_price: 현재 주가
        
        Returns:
            float or None: 가장 가까운 지지선 가격
        """
        if not self.support_levels:
            return None
        
        # 현재가보다 낮은 지지선만 필터링
        below_supports = [s for s in self.support_levels if s < current_price]
        
        if not below_supports:
            return None
        
        # 가장 가까운 것 선택
        return max(below_supports)
    
    def check_support_proximity(self, current_price, threshold_pct=3.0):
        """
        5차 필터: 지지선 근접도 체크
        
        Args:
            current_price: 현재 주가
            threshold_pct: 허용 범위 (기본 3%)
        
        Returns:
            dict: {'pass': bool, 'distance_pct': float, 'nearest_support': float, 'reason': str}
        """
        # 먼저 지지/저항선 계산
        if not self.support_levels:
            self.calculate_support_resistance()
        
        nearest_support = self.find_nearest_support(current_price)
        
        if nearest_support is None:
            return {
                'pass': True,  # 지지선 없으면 통과 (데이터 부족)
                'distance_pct': None,
                'nearest_support': None,
                'reason': '지지선 데이터 없음 (기본 통과)'
            }
        
        # 현재가와 지지선 사이 거리 (%)
        distance_pct = ((current_price - nearest_support) / nearest_support) * 100
        
        if distance_pct <= threshold_pct:
            return {
                'pass': True,
                'distance_pct': round(distance_pct, 2),
                'nearest_support': round(nearest_support, 2),
                'reason': f'지지선 근접 ({distance_pct:.1f}% 이내)'
            }
        else:
            return {
                'pass': False,
                'distance_pct': round(distance_pct, 2),
                'nearest_support': round(nearest_support, 2),
                'reason': f'지지선에서 멀리 떨어짐 ({distance_pct:.1f}%)'
            }


# 테스트 코드
if __name__ == "__main__":
    import yfinance as yf
    
    print("📊 SrVolumeFilter 테스트 중...")
    
    # 테스트 데이터 다운로드
    ticker = "AAPL"
    stock = yf.Ticker(ticker)
    df = stock.history(period='1y')
    
    # 필터 생성
    sr_filter = SrVolumeFilter(df, order=5)
    
    # 지지/저항선 계산
    levels = sr_filter.calculate_support_resistance()
    print(f"\n{ticker} 지지선: {levels['support'][:5]}")  # 상위 5개만 표시
    print(f"{ticker} 저항선: {levels['resistance'][:5]}")
    
    # 현재가 확인
    current_price = df['Close'].iloc[-1]
    print(f"\n현재가: ${current_price:.2f}")
    
    # 지지선 근접도 체크
    result = sr_filter.check_support_proximity(current_price, threshold_pct=3.0)
    print(f"\n필터 결과: {result}")
    
    if result['pass']:
        print(f"✅ 5차 필터 통과!")
    else:
        print(f"❌ 5차 필터 미통과")
