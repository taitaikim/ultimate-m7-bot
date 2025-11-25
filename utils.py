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
import time
import logging
from functools import wraps


try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


# ==========================================
# 보안 및 유틸리티 클래스
# ==========================================

def mask_api_key(key: str, show_chars: int = 4) -> str:
    """API 키를 마스킹하여 로그에 안전하게 출력합니다."""
    if not key or len(key) < show_chars * 2:
        return "***"
    return f"{key[:show_chars]}{'*' * (len(key) - show_chars * 2)}{key[-show_chars:]}"

class ConfigValidator:
    """설정 검증 클래스"""
    
    @staticmethod
    def load_config():
        """환경 변수 로드 및 검증"""
        load_dotenv()
        
        config = {
            'telegram_token': os.getenv('TELEGRAM_TOKEN'),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
            'google_api_key': os.getenv('GOOGLE_API_KEY'),
        }
        
        # 필수 변수 검증
        missing = [k for k, v in config.items() if not v]
        if missing:
            raise EnvironmentError(
                f"다음 환경 변수가 설정되지 않았습니다: {', '.join(missing)}\n"
                ".env 파일을 생성하거나 환경 변수를 설정하세요."
            )
        
        # API 키 형식 검증 (기본)
        if config['telegram_token'] and not config['telegram_token'][0].isdigit():
             logging.warning(f"Telegram 토큰 형식이 의심스럽습니다: {mask_api_key(config['telegram_token'])}")
        
        if config['google_api_key'] and not config['google_api_key'].startswith('AIza'):
             logging.warning(f"Google API 키 형식이 의심스럽습니다: {mask_api_key(config['google_api_key'])}")
        
        return config

class RateLimiter:
    """API 레이트 리미터"""
    
    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            self.calls = [c for c in self.calls if now - c < self.period]
            
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    logging.warning(f"Rate limit reached. Sleeping {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                self.calls = []
            
            self.calls.append(now)
            return func(*args, **kwargs)
        return wrapper

def retry(max_attempts: int = 3, backoff_factor: float = 2.0):
    """재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
                    last_exception = e
                    wait_time = backoff_factor ** attempt
                    
                    logging.warning(
                        f"{func.__name__} 실패 (시도 {attempt + 1}/{max_attempts}). "
                        f"{wait_time:.1f}초 후 재시도..."
                    )
                    
                    if attempt < max_attempts - 1:
                        time.sleep(wait_time)
                    
                except Exception as e:
                    # 재시도 불가능한 에러는 즉시 발생
                    logging.error(f"{func.__name__} 치명적 오류: {e}")
                    raise
            
            # 모든 재시도 실패
            logging.error(f"{func.__name__} {max_attempts}회 시도 모두 실패")
            raise last_exception
        
        return wrapper
    return decorator

class DataValidator:
    """데이터 검증기"""
    
    @staticmethod
    def validate_stock_data(ticker: str, data: dict) -> tuple[bool, str]:
        """
        주식 데이터 검증
        
        Returns:
            (is_valid, error_message)
        """
        # 1. 필수 필드 확인
        required_fields = ['price', 'rsi', 'volume']
        missing = [f for f in required_fields if f not in data]
        if missing:
            return False, f"Missing fields: {missing}"
        
        # 2. 가격 범위 확인
        if not (0.01 <= data['price'] <= 100000):
            return False, f"Invalid price: {data['price']}"
        
        # 3. RSI 범위 확인
        if not (0 <= data['rsi'] <= 100):
            return False, f"Invalid RSI: {data['rsi']}"
        
        # 4. 거래량 확인
        if data['volume'] < 0:
            return False, f"Invalid volume: {data['volume']}"
        
        return True, ""

class SmartAlertManager:
    """쿨다운 + 상태 변화 통합 알림 관리자"""
    
    def __init__(self, cooldown_minutes: int = 60):
        self.cooldown_minutes = cooldown_minutes
        self.last_alerts = {}
        self.states = {}
    
    def should_alert(self, ticker: str, rsi: float) -> tuple[bool, str]:
        """
        알림 발송 여부 및 이유
        
        Returns:
            (should_alert, reason)
        """
        now = datetime.now()
        
        # 1. 상태 변화 확인
        new_state = self._get_state(rsi)
        old_state = self.states.get(ticker, 'normal')
        state_changed = old_state != new_state
        
        # 2. 쿨다운 확인
        last_alert = self.last_alerts.get(ticker)
        cooldown_passed = (
            not last_alert or 
            (now - last_alert).seconds // 60 >= self.cooldown_minutes
        )
        
        # 3. 알림 결정
        if state_changed and new_state != 'normal':
            # 상태 변화 시 즉시 알림 (쿨다운 무시)
            self._update(ticker, now, new_state)
            return True, f"상태 변경: {old_state} → {new_state}"
        
        elif new_state != 'normal' and cooldown_passed:
            # 쿨다운 지났으면 재알림
            self._update(ticker, now, new_state)
            return True, f"정기 알림 (RSI {new_state})"
        
        else:
            # 알림 불필요
            return False, "쿨다운 중 또는 정상 상태"
    
    def _get_state(self, rsi: float) -> str:
        if rsi < 30:
            return 'oversold'
        elif rsi > 70:
            return 'overbought'
        else:
            return 'normal'
    
    def _update(self, ticker: str, timestamp: datetime, state: str):
        self.last_alerts[ticker] = timestamp
        self.states[ticker] = state


# ==========================================
# 환경 변수 로딩
# ==========================================

def load_env_vars():
    """
    .env 파일에서 설정을 로드하고 검증합니다.
    
    Returns:
        tuple: (BOT_TOKEN, CHAT_ID)
    """
    try:
        config = ConfigValidator.load_config()
        return config['telegram_token'], config['telegram_chat_id']
    except EnvironmentError as e:
        print(f"❌ 설정 오류: {e}")
        return None, None


# ==========================================
# 데이터 수집
# ==========================================

@retry(max_attempts=3, backoff_factor=2.0)
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

@RateLimiter(max_calls=20, period=60)
@retry(max_attempts=3, backoff_factor=2.0)
def send_telegram_alert(bot_token, chat_id, message, parse_mode=None):
    """
    텔레그램 채팅방으로 메시지를 전송합니다.
    재시도 로직은 @retry 데코레이터가 처리합니다.
    
    Args:
        bot_token (str): 텔레그램 봇 토큰
        chat_id (str): 텔레그램 채팅 ID
        message (str): 전송할 메시지 (HTML, Markdown, 또는 일반 텍스트)
        parse_mode (str): 메시지 파싱 모드 ('HTML', 'Markdown', 또는 None)
                         None이면 일반 텍스트로 전송
    
    Returns:
        tuple: (성공 여부(bool), 메시지(str))
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    
    # parse_mode가 지정된 경우에만 추가
    if parse_mode:
        data["parse_mode"] = parse_mode
    
    # 타임아웃 30초로 증가
    response = requests.post(url, data=data, timeout=30)
    
    if response.status_code == 200:
        return True, "메시지 전송 성공"
    else:
        # 4xx, 5xx 에러 발생 시 예외를 던져서 retry가 잡도록 함
        response.raise_for_status()
        return False, f"API 에러 (코드: {response.status_code})"


# ==========================================
# 메시지 포맷팅 헬퍼
# ==========================================

def format_scanner_alert(ticker, price, rsi, reason, ai_comment=None):
    """
    텔레그램 알림 메시지 포맷 (일반 텍스트 버전)
    AI 코멘트가 있으면 함께 출력합니다.
    """
    # 기본 메시지
    message = f"""
M7 Auto Scanner Alert

Ticker: {ticker}
Price: ${price:.2f}
RSI: {rsi:.1f}

Signal: {reason}
"""

    # AI 코멘트가 있으면 추가
    if ai_comment:
        message += f"\nAI Insight:\n{ai_comment}\n"

    # 시간 추가
    message += f"\nDetected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
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
• Stop Loss: ${stop_loss:.2f}
• Take Profit: ${take_profit:.2f}

<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""


# ==========================================
# AI ANALYST (Gemini)
# ==========================================

@RateLimiter(max_calls=10, period=60)
def get_ai_analysis(ticker, rsi, price):
    """
    구글 Gemini에게 시장 분석 요청
    
    Args:
        ticker (str): 종목 티커
        rsi (float): RSI 값
        price (float): 현재가
    
    Returns:
        str: AI 분석 결과 또는 에러 메시지
    """
    if not GENAI_AVAILABLE:
        return "AI 라이브러리 미설치"
    
    try:
        # .env 파일 다시 로드 (중요!)
        load_dotenv()
        
        # API 키 확인
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "AI 키 미설정"

        # Gemini 설정
        genai.configure(api_key=api_key)
        
        # 안정적인 모델 사용
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        
        # 간결한 프롬프트 (월가 퀀트 트레이더 페르소나)
        prompt = f"""
        역할: 너는 20년 경력의 냉철한 월스트리트 퀀트 트레이더야.
        상황: {ticker} 현재가 ${price:.2f}, RSI {rsi:.1f}.
        
        지시사항:
        1. 감정을 섞지 말고 건조하고 분석적인 어조(Dry & Analytical tone)로 말해.
        2. '기술적 해석'에는 반드시 '지지선/저항선'이나 '추세' 같은 전문 용어를 포함해.
        3. '조언'은 매수/매도/관망 중 하나의 포지션을 명확히 암시해.
        
        형식: 이모지를 사용하여 한국어로 딱 2줄로 요약할 것.
        """
        
        # 안전 설정 추가 (모두 허용)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        # AI 응답 생성
        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config={
                'temperature': 0.7,
                'max_output_tokens': 200,
            }
        )
        
        # 응답 텍스트 정리
        ai_text = response.text.strip()
        
        # 3줄 이상이면 앞 2줄만 사용
        lines = [line for line in ai_text.split('\n') if line.strip()]
        if len(lines) > 2:
            ai_text = '\n'.join(lines[:2])
        
        return ai_text
        
    except Exception as e:
        # 에러 메시지 간결하게
        error_msg = str(e)
        if "404" in error_msg:
            return "AI 모델 오류"
        elif "API_KEY" in error_msg or "credentials" in error_msg.lower():
            return "AI API 키 오류"
        else:
            return f"AI 분석 실패: {error_msg[:30]}"


@RateLimiter(max_calls=10, period=60)
def get_ai_vision_analysis(image_data):
    """
    GPT-4 Vision을 사용하여 스크린샷에서 포트폴리오 정보를 추출합니다.
    
    Args:
        image_data (bytes): 이미지 바이너리 데이터
    
    Returns:
        str: JSON 형식의 추출 데이터 또는 에러 메시지
    """
    try:
        import openai
        import base64
        
        # .env 파일 다시 로드
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return '{"positions": [], "error": "OpenAI API 키 미설정 (.env에 OPENAI_API_KEY 추가 필요)"}'

        # 이미지를 base64로 인코딩
        img_base64 = base64.b64encode(image_data).decode()
        
        # GPT-4 Vision API 호출
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",  # 더 높은 정확도를 위해 gpt-4o 사용
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """
You are a precise OCR system for Korean stock trading app screenshots.

**TASK:** Extract ONLY these 3 values for each stock position:
1. **Ticker** (종목명)
2. **Quantity** (보유수량) - INTEGER only
3. **Average Price** (평균단가/매입단가) - DECIMAL number

**CRITICAL RULES FOR NUMBERS:**
1. Korean numbers use COMMA as thousands separator: 1,234,567
2. REMOVE all commas before converting to number
3. For Korean stocks (KRW): prices are usually 10,000-100,000 range
4. For US stocks (USD): prices are usually 50-500 range
5. If you see "원" (won), it's Korean price
6. Quantity is ALWAYS a whole number (no decimals)

**COLUMN MAPPING:**
- "보유수량" or "수량" → quantity
- "평균단가" or "매입단가" → avg_price
- IGNORE "평가금액", "평가손익", "수익률" (these are calculated values)

**EXAMPLES:**
Input: "삼성전자, 보유수량: 50주, 평균단가: 72,500원"
Output: {"ticker": "삼성전자", "quantity": 50, "avg_price": 72500}

Input: "NVDA, Qty: 10, Avg: 145.50"
Output: {"ticker": "NVDA", "quantity": 10, "avg_price": 145.50}

Input: "AAPL, 수량: 25, 단가: 180.25"
Output: {"ticker": "AAPL", "quantity": 25, "avg_price": 180.25}

**OUTPUT FORMAT (JSON only, no markdown):**
{
    "positions": [
        {"ticker": "NVDA", "quantity": 10, "avg_price": 145.50},
        {"ticker": "삼성전자", "quantity": 50, "avg_price": 72500}
    ],
    "confidence": 0.95,
    "debug_info": "Found 2 positions in Korean brokerage app"
}

**IMPORTANT:**
- Return ONLY JSON (no ```json``` markdown)
- Use exact numbers from image (don't round or estimate)
- Quantity must be integer
- Price must be decimal (use .0 if whole number)
- Keep Korean stock names in Korean
- Keep US stock tickers in English
                            """
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0  # 정확도를 위해 temperature를 0으로 설정
        )
        
        # JSON 파싱
        result_text = response.choices[0].message.content.strip()
        
        # 마크다운 코드 블록 제거
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        return result_text.strip()
        
    except Exception as e:
        logging.error(f"GPT-4 Vision Analysis Error: {e}")
        return f'{{"positions": [], "error": "분석 실패: {str(e)[:100]}"}}'
