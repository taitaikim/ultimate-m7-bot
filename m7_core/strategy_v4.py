import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

class TrendlineStrategy:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
    
    def get_peaks(self, window=10):
        """
        주가의 고점(Peaks)을 찾아내는 함수 (Local Maxima)
        """
        prices = self.df['Close'].values
        # window 간격으로 로컬 고점을 탐색
        peaks_idx = argrelextrema(prices, np.greater, order=window)[0]
        return peaks_idx

    def calculate_resistance_line(self, lookback=60):
        """
        최근 고점들을 연결하여 저항 추세선(Resistance Line)을 계산
        """
        # 최근 N일 데이터만 사용
        recent_df = self.df.iloc[-lookback:].copy()
        peaks = self.get_peaks(window=5) # 민감도 조절 (5일 간격 고점)
        
        # 데이터 범위 내의 고점만 필터링
        valid_peaks = [p for p in peaks if p >= (len(self.df) - lookback)]
        
        if len(valid_peaks) < 2:
            return None, None # 추세선을 그릴 포인트 부족
            
        # 마지막 두 개의 주요 고점을 연결 (단순화된 로직)
        x1, x2 = valid_peaks[-2], valid_peaks[-1]
        y1, y2 = self.df['Close'].iloc[x1], self.df['Close'].iloc[x2]
        
        # 기울기(Slope)와 절편(Intercept) 계산
        # y = mx + c
        if x2 == x1: return None, None # 수직선 예외처리
        
        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - (slope * x1)
        
        return slope, intercept

    def check_breakout(self):
        """
        현재가가 추세선을 돌파했는지 판별
        """
        slope, intercept = self.calculate_resistance_line()
        
        if slope is None:
            return False, 0.0
        
        current_idx = len(self.df) - 1
        current_price = self.df['Close'].iloc[-1]
        
        # 추세선상의 현재 위치 가격 계산
        trendline_price = (slope * current_idx) + intercept
        
        # 하락 추세선(기울기 음수)이고, 현재가가 추세선을 뚫었을 때
        is_breakout = (slope < 0) and (current_price > trendline_price)
        
        return is_breakout, trendline_price

class RiskManager:
    @staticmethod
    def calculate_position_size(account_balance, risk_per_trade_pct, atr_value, stop_loss_atr_multiplier=2.0):
        """
        ATR 기반 포지션 사이징 계산기
        공식: (총자본 * 리스크%) / (ATR * 배수)
        """
        if atr_value <= 0: return 0
        
        risk_amount = account_balance * (risk_per_trade_pct / 100.0)
        stop_loss_distance = atr_value * stop_loss_atr_multiplier
        
        if stop_loss_distance == 0: return 0
        
        shares = risk_amount / stop_loss_distance
        return int(shares) # 주식 수는 정수여야 함
