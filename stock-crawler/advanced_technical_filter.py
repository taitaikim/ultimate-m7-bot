import numpy as np
import pandas as pd
from scipy.signal import find_peaks, argrelextrema
from scipy.ndimage import gaussian_filter1d
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class AdvancedTechnicalFilter:
    """
    고급 기술적 분석 필터 클래스
    - 지지선/저항선 탐지
    - 매물대 분석 (Volume Profile / POC)
    - Plotly 차트 생성
    """
    
    def __init__(self, ticker, df, current_price):
        """
        Args:
            ticker (str): 종목 티커
            df (pd.DataFrame): OHLCV 데이터 (columns: Open, High, Low, Close, Volume)
            current_price (float): 현재 주가
        """
        self.ticker = ticker
        self.df = df.copy()
        self.current_price = current_price
        
        # 분석 결과 저장
        self.support_levels = []
        self.resistance_levels = []
        self.poc_price = None
        self.volume_profile = None
        
    def find_support_resistance(self, lookback=120, prominence=0.02):
        """
        지지선과 저항선을 탐지합니다.
        
        Args:
            lookback (int): 분석할 과거 데이터 기간 (일)
            prominence (float): 피크 탐지 민감도 (가격 변동의 %)
        
        Returns:
            dict: {'support': [...], 'resistance': [...]}
        """
        # 최근 lookback 기간 데이터만 사용
        recent_df = self.df.tail(lookback).copy()
        
        if len(recent_df) < 30:
            return {'support': [], 'resistance': []}
        
        # High/Low 가격 추출
        highs = recent_df['High'].values
        lows = recent_df['Low'].values
        closes = recent_df['Close'].values
        
        # 가격 범위 기반 prominence 계산
        price_range = np.max(closes) - np.min(closes)
        min_prominence = price_range * prominence
        
        # 저항선 탐지 (High의 local maxima)
        resistance_idx, properties = find_peaks(highs, prominence=min_prominence, distance=5)
        
        # 지지선 탐지 (Low의 local minima, 역으로 찾기)
        support_idx, properties = find_peaks(-lows, prominence=min_prominence, distance=5)
        
        # 지지선/저항선 레벨 추출 및 강도 계산
        resistance_levels = []
        for idx in resistance_idx:
            price = highs[idx]
            strength = self._calculate_level_strength(price, highs, lows, closes)
            resistance_levels.append({
                'price': price,
                'strength': strength,
                'type': 'resistance'
            })
        
        support_levels = []
        for idx in support_idx:
            price = lows[idx]
            strength = self._calculate_level_strength(price, highs, lows, closes)
            support_levels.append({
                'price': price,
                'strength': strength,
                'type': 'support'
            })
        
        # 가격 클러스터링 (유사한 레벨 통합)
        self.support_levels = self._cluster_levels(support_levels)
        self.resistance_levels = self._cluster_levels(resistance_levels)
        
        return {
            'support': self.support_levels,
            'resistance': self.resistance_levels
        }
    
    def _calculate_level_strength(self, level_price, highs, lows, closes, tolerance=0.02):
        """
        특정 가격 레벨의 강도를 계산합니다 (터치 횟수 기반).
        
        Args:
            level_price (float): 레벨 가격
            highs, lows, closes (np.array): 가격 데이터
            tolerance (float): 레벨 인식 허용 오차 (2%)
        
        Returns:
            str: '상', '중', '하'
        """
        threshold = level_price * tolerance
        
        # 해당 레벨을 터치한 횟수 계산
        touches = 0
        for h, l in zip(highs, lows):
            if abs(h - level_price) <= threshold or abs(l - level_price) <= threshold:
                touches += 1
        
        # 강도 분류
        if touches >= 4:
            return '상'
        elif touches >= 2:
            return '중'
        else:
            return '하'
    
    def _cluster_levels(self, levels, tolerance=0.015):
        """
        유사한 가격 레벨을 클러스터링하여 통합합니다.
        
        Args:
            levels (list): [{'price': ..., 'strength': ..., 'type': ...}, ...]
            tolerance (float): 클러스터링 허용 오차 (1.5%)
        
        Returns:
            list: 통합된 레벨 리스트
        """
        if not levels:
            return []
        
        # 가격 순으로 정렬
        sorted_levels = sorted(levels, key=lambda x: x['price'])
        
        clustered = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # 현재 클러스터의 평균 가격
            cluster_avg = np.mean([l['price'] for l in current_cluster])
            
            # 허용 오차 내에 있으면 클러스터에 추가
            if abs(level['price'] - cluster_avg) / cluster_avg <= tolerance:
                current_cluster.append(level)
            else:
                # 클러스터 완료, 대표값 저장
                clustered.append(self._merge_cluster(current_cluster))
                current_cluster = [level]
        
        # 마지막 클러스터 추가
        if current_cluster:
            clustered.append(self._merge_cluster(current_cluster))
        
        return clustered
    
    def _merge_cluster(self, cluster):
        """클러스터 내 레벨들을 하나로 병합"""
        avg_price = np.mean([l['price'] for l in cluster])
        
        # 강도는 가장 높은 것으로
        strengths = [l['strength'] for l in cluster]
        if '상' in strengths:
            strength = '상'
        elif '중' in strengths:
            strength = '중'
        else:
            strength = '하'
        
        return {
            'price': avg_price,
            'strength': strength,
            'type': cluster[0]['type'],
            'count': len(cluster)
        }
    
    def calculate_volume_profile(self, lookback=60, bins=50):
        """
        매물대 분석 (Volume Profile)을 수행하고 POC를 찾습니다.
        
        Args:
            lookback (int): 분석 기간
            bins (int): 가격 구간 개수
        
        Returns:
            dict: {'poc': POC 가격, 'profile': 매물대 데이터}
        """
        recent_df = self.df.tail(lookback).copy()
        
        if len(recent_df) < 10:
            return {'poc': None, 'profile': None}
        
        # 가격 범위 설정
        price_min = recent_df['Low'].min()
        price_max = recent_df['High'].max()
        
        # 가격 구간 생성
        price_bins = np.linspace(price_min, price_max, bins)
        volume_at_price = np.zeros(bins - 1)
        
        # 각 구간별 거래량 집계
        for _, row in recent_df.iterrows():
            # 해당 봉의 가격 범위
            low, high, volume = row['Low'], row['High'], row['Volume']
            
            # 가격 범위 내 구간들에 거래량 분배
            for i in range(len(price_bins) - 1):
                bin_low, bin_high = price_bins[i], price_bins[i + 1]
                
                # 겹치는 구간 계산
                overlap_low = max(low, bin_low)
                overlap_high = min(high, bin_high)
                
                if overlap_high > overlap_low:
                    # 겹치는 비율만큼 거래량 할당
                    overlap_ratio = (overlap_high - overlap_low) / (high - low) if high > low else 1
                    volume_at_price[i] += volume * overlap_ratio
        
        # POC (Point of Control) - 거래량이 가장 많은 가격
        poc_idx = np.argmax(volume_at_price)
        poc_price = (price_bins[poc_idx] + price_bins[poc_idx + 1]) / 2
        
        self.poc_price = poc_price
        self.volume_profile = {
            'prices': [(price_bins[i] + price_bins[i + 1]) / 2 for i in range(len(price_bins) - 1)],
            'volumes': volume_at_price.tolist()
        }
        
        return {
            'poc': poc_price,
            'profile': self.volume_profile
        }
    
    def check_buy_conditions(self, support_tolerance=0.03, resistance_range=0.05):
        """
        고급 매수 조건을 체크합니다.
        
        조건:
        1. 현재가가 주요 지지선 +3% 이내
        2. 현재가 위 5% 구간 내에 강한 저항선 없음
        
        Args:
            support_tolerance (float): 지지선 근접 허용 범위 (3%)
            resistance_range (float): 상단 저항 체크 범위 (5%)
        
        Returns:
            dict: {
                'near_support': bool,
                'support_info': {...},
                'no_overhead_resistance': bool,
                'resistance_info': {...},
                'buy_approved': bool
            }
        """
        result = {
            'near_support': False,
            'support_info': None,
            'no_overhead_resistance': False,
            'resistance_info': None,
            'buy_approved': False
        }
        
        # 조건 1: 지지선 근접 체크
        nearest_support = None
        min_distance = float('inf')
        
        for support in self.support_levels:
            distance_pct = (self.current_price - support['price']) / support['price']
            
            # 지지선 위에 있고, 3% 이내
            if 0 <= distance_pct <= support_tolerance:
                if distance_pct < min_distance:
                    min_distance = distance_pct
                    nearest_support = support
        
        if nearest_support:
            result['near_support'] = True
            result['support_info'] = {
                'price': nearest_support['price'],
                'strength': nearest_support['strength'],
                'distance_pct': min_distance * 100
            }
        
        # 조건 2: 상단 저항 체크
        overhead_resistance = []
        upper_bound = self.current_price * (1 + resistance_range)
        
        for resistance in self.resistance_levels:
            if self.current_price < resistance['price'] <= upper_bound:
                # 강한 저항만 필터링 (강도 '상' 또는 '중')
                if resistance['strength'] in ['상', '중']:
                    overhead_resistance.append(resistance)
        
        if len(overhead_resistance) == 0:
            result['no_overhead_resistance'] = True
        else:
            result['resistance_info'] = {
                'count': len(overhead_resistance),
                'nearest': min(overhead_resistance, key=lambda x: x['price'])
            }
        
        # 최종 승인
        result['buy_approved'] = result['near_support'] and result['no_overhead_resistance']
        
        return result
    
    def generate_plotly_chart(self, ma20=None, ma60=None):
        """
        Plotly 인터랙티브 차트를 생성합니다.
        
        Args:
            ma20, ma60 (pd.Series): 이동평균선 데이터
        
        Returns:
            str: Plotly HTML div 문자열
        """
        # 최근 120일 데이터
        plot_df = self.df.tail(120).copy()
        
        # 서브플롯 생성 (가격 차트 + 거래량)
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f'{self.ticker} - 고급 기술적 분석', '거래량')
        )
        
        # 캔들스틱 차트
        fig.add_trace(
            go.Candlestick(
                x=plot_df.index,
                open=plot_df['Open'],
                high=plot_df['High'],
                low=plot_df['Low'],
                close=plot_df['Close'],
                name='Price',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=1, col=1
        )
        
        # 이동평균선
        if ma20 is not None:
            fig.add_trace(
                go.Scatter(
                    x=plot_df.index,
                    y=ma20.tail(120),
                    mode='lines',
                    name='MA20',
                    line=dict(color='orange', width=1.5)
                ),
                row=1, col=1
            )
        
        if ma60 is not None:
            fig.add_trace(
                go.Scatter(
                    x=plot_df.index,
                    y=ma60.tail(120),
                    mode='lines',
                    name='MA60',
                    line=dict(color='blue', width=1.5)
                ),
                row=1, col=1
            )
        
        # 지지선 표시
        for support in self.support_levels:
            color = 'green' if support['strength'] == '상' else 'lightgreen'
            fig.add_hline(
                y=support['price'],
                line=dict(color=color, width=2, dash='dash'),
                annotation_text=f"지지 ${support['price']:.2f} ({support['strength']})",
                annotation_position="right",
                row=1, col=1
            )
        
        # 저항선 표시
        for resistance in self.resistance_levels:
            color = 'red' if resistance['strength'] == '상' else 'lightcoral'
            fig.add_hline(
                y=resistance['price'],
                line=dict(color=color, width=2, dash='dash'),
                annotation_text=f"저항 ${resistance['price']:.2f} ({resistance['strength']})",
                annotation_position="right",
                row=1, col=1
            )
        
        # POC 표시
        if self.poc_price:
            fig.add_hline(
                y=self.poc_price,
                line=dict(color='purple', width=3, dash='dot'),
                annotation_text=f"POC ${self.poc_price:.2f}",
                annotation_position="left",
                row=1, col=1
            )
        
        # 현재가 표시
        fig.add_hline(
            y=self.current_price,
            line=dict(color='black', width=2),
            annotation_text=f"현재가 ${self.current_price:.2f}",
            annotation_position="left",
            row=1, col=1
        )
        
        # 거래량 차트
        colors = ['red' if row['Close'] < row['Open'] else 'green' for _, row in plot_df.iterrows()]
        fig.add_trace(
            go.Bar(
                x=plot_df.index,
                y=plot_df['Volume'],
                name='Volume',
                marker_color=colors,
                showlegend=False
            ),
            row=2, col=1
        )
        
        # 레이아웃 설정
        fig.update_layout(
            height=700,
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        fig.update_xaxes(title_text="날짜", row=2, col=1)
        fig.update_yaxes(title_text="가격 ($)", row=1, col=1)
        fig.update_yaxes(title_text="거래량", row=2, col=1)
        
        # HTML div로 변환
        return fig.to_html(include_plotlyjs='cdn', div_id=f'chart_{self.ticker}')
