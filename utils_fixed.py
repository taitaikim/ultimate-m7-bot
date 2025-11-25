"""
M7 Bot - 공통 유틸리티 함수 모음
데이터 수집, 기술적 지표 계산, 텔레그램 알림 등의 공통 로직을 제공합니다.
"""

import os
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai  # 라이브러리 추가


# ==========================================
# 환경 변수 로딩
# ==========================================

def load_env_vars():
    """
    .env 파일에서 텔레그램 토큰과 채팅 ID를 로드합니다.
    
    Returns:
        tuple: (BOT_TOKEN, CHAT_ID) 또는 실패 시 (None, None)
    """
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    return bot_token, chat_id


# ==========================================
# 데이터 수집
# ==========================================

def get_stock_data(ticker, period="6mo"):
    """
    yfinance를 사용하여 주식 데이터를 수집합니다.
    MultiIndex 컬럼을 자동으로 처리합니다.
    
    Args:
        ticker (str): 주식 티커 심볼 (예: 'NVDA', 'AAPL')
        period (str): 데이터 기간 (예: '1y', '6mo', '3mo')
    
    Returns:
        pd.DataFrame: 주가 데이터 (Open, High, Low, Close, Volume)
                      실패 시 빈 DataFrame 반환
    """
    try:
       # auto_adjust=True 추가!
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        
        # MultiIndex 컬럼 처리 (여러 티커 동시 다운로드 시 발생)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        return df
    
    except Exception as e:
        print(f"❌ 데이터 수집 실패 ({ticker}): {e}")
        return pd.DataFrame()


# ==========================================
# 기술적 지표 계산
# ==========================================

def calculate_rsi(df, period=14):
    """
    Wilder's Smoothing(EMA) 방식으로 RSI를 계산합니다.
    
    Args:
        df (pd.DataFrame): 'Close' 컬럼을 포함한 DataFrame
        period (int): RSI 계산 기간 (기본값: 14)
    
    Returns:
        pd.Series: RSI 값 (0-100 범위)
    """
    close = df['Close']
    delta = close.diff()
    
    # 상승분/하락분 분리
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    
    # RS 및 RSI 계산
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_moving_averages(df):
    """
    이동평균선(MA20, MA200)을 계산합니다.
    
    Args:
        df (pd.DataFrame): 'Close' 컬럼을 포함한 DataFrame
    
    Returns:
        dict: {'MA20': Series, 'MA200': Series}
    """
    return {
        'MA20': df['Close'].rolling(window=20).mean(),
        'MA200': df['Close'].rolling(window=200).mean()
    }


def calculate_macd(df):
    """
    MACD 지표를 계산합니다.
    
    Args:
        df (pd.DataFrame): 'Close' 컬럼을 포함한 DataFrame
    
    Returns:
        dict: {'MACD': Series, 'Signal': Series, 'Hist': Series}
    """
    close = df['Close']
    
    exp12 = close.ewm(span=12, adjust=False).mean()
    exp26 = close.ewm(span=26, adjust=False).mean()
    
    macd = exp12 - exp26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    
    return {
        'MACD': macd,
        'Signal': signal,
        'Hist': hist
    }


def calculate_atr(df, period=14):
    """
    Average True Range (ATR)를 계산합니다.
    
    Args:
        df (pd.DataFrame): 'High', 'Low', 'Close' 컬럼을 포함한 DataFrame
        period (int): ATR 계산 기간 (기본값: 14)
    
    Returns:
        pd.Series: ATR 값
    """
    # True Range 계산
    tr = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift()).abs(),
        (df['Low'] - df['Close'].shift()).abs()
    ], axis=1).max(axis=1)
    
    # ATR = TR의 이동평균
    atr = tr.rolling(window=period).mean()
    
    return atr


def calculate_metrics(df):
    """
    모든 기술적 지표를 한 번에 계산합니다.
    (RSI, MA20, MA200, MACD, ATR, Volume Average, Support, Resistance)
    
    Args:
        df (pd.DataFrame): OHLCV 데이터를 포함한 DataFrame
    
    Returns:
        pd.DataFrame: 모든 지표가 추가된 DataFrame
    """
    if df.empty:
        return df
    
    # RSI (Wilder's Smoothing)
    df['RSI'] = calculate_rsi(df)
    
    # 이동평균
    mas = calculate_moving_averages(df)
    df['MA20'] = mas['MA20']
    df['MA200'] = mas['MA200']
    
    # MACD
    macd = calculate_macd(df)
    df['MACD'] = macd['MACD']
    df['Signal'] = macd['Signal']
    df['Hist'] = macd['Hist']
    
    # ATR
    df['ATR'] = calculate_atr(df)
    
    # True Range (ATR 계산에 이미 사용되었지만 별도 저장)
    df['TR'] = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift()).abs(),
        (df['Low'] - df['Close'].shift()).abs()
    ], axis=1).max(axis=1)
    
    # Volume Average
    df['VolAvg'] = df['Volume'].rolling(window=20).mean()
    
    # Support & Resistance (최근 20일 기준)
    df['Support'] = df['Low'].rolling(window=20).min()
    df['Resistance'] = df['High'].rolling(window=20).max()
    
    return df


# ==========================================
# 텔레그램 알림
# ==========================================

def send_telegram_alert(bot_token, chat_id, message, parse_mode=None):
    """
    텔레그램 채팅방으로 메시지를 전송합니다.
    
    Args:
        bot_token (str): 텔레그램 봇 토큰
        chat_id (str): 텔레그램 채팅 ID
        message (str): 전송할 메시지 (HTML, Markdown, 또는 일반 텍스트)
        parse_mode (str): 메시지 파싱 모드 ('HTML', 'Markdown', 또는 None)
                         None이면 일반 텍스트로 전송
    
    Returns:
        tuple: (성공 여부(bool), 메시지(str))
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message
        }
        
        # parse_mode가 지정된 경우에만 추가
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            return True, "메시지 전송 성공"
        else:
            return False, f"API 에러 (코드: {response.status_code})"
    
    except requests.exceptions.Timeout:
        return False, "타임아웃: 10초 내 응답 없음"
    
    except Exception as e:
        return False, f"예외 발생: {str(e)}"


# ==========================================
# 메시지 포맷팅 헬퍼
# ==========================================

def format_scanner_alert(ticker, price, rsi, reason, ai_comment=None):
    """
    텔레그램 알림 메시지 포맷 (Option B: 깔끔한 텍스트 버전)
    AI 코멘트가 있으면 함께 출력합니다.
    """
    from datetime import datetime
    
    # 기본 메시지
    message = f"""
🚨 M7 Auto Scanner Alert

🎯 Ticker: {ticker}
💵 Price: ${price:.2f}
📊 RSI: {rsi:.1f}

🔥 Signal: {reason}
"""

    # AI 코멘트가 있으면 추가
    if ai_comment:
        message += f"\n🤖 AI Insight:\n{ai_comment}\n"

    # 시간 추가
    message += f"\n⏰ Detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return message


def format_dashboard_alert(ticker, price, score, reason, stop_loss, take_profit):
    """
    대시보드용 텔레그램 알림 메시지를 포맷팅합니다.
    
    Args:
        ticker (str): 종목 티커
        price (float): 진입가
        score (int): 시그널 점수
        reason (str): 시그널 사유
        stop_loss (float): 손절가
        take_profit (float): 익절가
    
    Returns:
        str: HTML 형식의 포맷된 메시지
    """
    return f"""
🚀 <b>M7 Dashboard Alert</b>

🎯 <b>Ticker:</b> {ticker}
💵 <b>Price:</b> ${price:.2f}
📊 <b>Score:</b> {score}/100

📈 <b>Signal:</b>
{reason}

🛡️ <b>Strategy:</b>
"""
    Args:
