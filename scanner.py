"""
M7 Auto Scanner - Background Monitoring Service
배경에서 지속적으로 실행되며 5분마다 시장 조건을 체크합니다.
RSI 조건이 충족되면 자동으로 텔레그램 알림을 전송합니다.
"""

import time
import logging
from datetime import datetime
import utils  # 공통 유틸리티 함수 임포트

# ==========================================
# 로깅 설정
# ==========================================

# 로거 생성
logger = logging.getLogger('M7Scanner')
logger.setLevel(logging.INFO)

# 콘솔 핸들러 (터미널 출력)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# 파일 핸들러 (scanner.log 파일 저장)
file_handler = logging.FileHandler('scanner.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# 핸들러 등록
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# ==========================================
# 설정
# ==========================================

CHECK_INTERVAL = 300  # 5분 (초 단위)
COOLDOWN_PERIOD = 3600  # 1시간 (초 단위) - 중복 알림 방지

TARGET_TICKERS = [
    'NVDA', 'TSLA', 'META', 'AMZN', 'GOOGL', 'AAPL', 'MSFT',  # M7
    'QQQ', 'TQQQ', 'XLK'  # ETFs
]

# 텔레그램 credentials 로드
BOT_TOKEN, CHAT_ID = utils.load_env_vars()

if not BOT_TOKEN or not CHAT_ID:
    logger.error("❌ .env 파일에서 TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID를 찾을 수 없습니다.")
    exit(1)

logger.info(f"✅ 텔레그램 credentials 로드 완료")

# ==========================================
# 핵심 로직
# ==========================================

def check_ticker(ticker, smart_alert):
    """
    단일 티커를 체크하고 조건 충족 시 알림을 전송합니다.
    
    Args:
        ticker (str): 종목 티커
        smart_alert (SmartAlertManager): 알림 관리자 인스턴스
    
    Returns:
        bool: 알림 전송 여부
    """
    try:
        # 데이터 수집 (6개월)
        df = utils.get_stock_data(ticker, period="6mo")
        
        if df.empty:
            logger.warning(f"⚠️  {ticker}: 데이터 수집 실패")
            return False
        
        # 데이터 검증 (DataValidator)
        # 최근 데이터만 추출하여 검증
        latest_data = {
            'price': df['Close'].iloc[-1],
            'volume': df['Volume'].iloc[-1],
            'rsi': 50.0 # 임시 값 (RSI 계산 전이라)
        }
        
        # RSI 계산
        rsi_series = utils.calculate_rsi(df)
        rsi = rsi_series.iloc[-1]
        latest_data['rsi'] = rsi # 실제 RSI 값 업데이트
        
        # 유효성 검사
        is_valid, error_msg = utils.DataValidator.validate_stock_data(ticker, latest_data)
        if not is_valid:
            logger.warning(f"⚠️  {ticker} 데이터 유효성 오류: {error_msg}")
            return False
            
        price = latest_data['price']
        
        # 알림 여부 확인 (SmartAlertManager)
        should_alert, reason = smart_alert.should_alert(ticker, rsi)
        
        if should_alert:
            # [NEW] 🧠 AI에게 분석 요청 (여기가 핵심!)
            logger.info(f"🧠 AI 분석 요청 중... ({ticker})")
            ai_comment = utils.get_ai_analysis(ticker, rsi, price)
            
            # 메시지 포맷팅
            message = utils.format_scanner_alert(ticker, price, rsi, reason, ai_comment)
            
            # 텔레그램 전송
            success, msg = utils.send_telegram_alert(BOT_TOKEN, CHAT_ID, message)
            
            if success:
                logger.info(f"✅ 알림 전송 성공: {ticker} (RSI: {rsi:.1f})")
                return True
            else:
                logger.error(f"❌ 알림 전송 실패: {ticker} - {msg}")
                return False
        else:
            # 조건 미충족 또는 쿨다운
            if "쿨다운" in reason:
                # 쿨다운 중일 때는 로그 레벨을 낮추거나 생략 가능
                pass 
            else:
                logger.info(f"   {ticker}: ${price:.2f} | RSI: {rsi:.1f} ({reason})")
            return False
    
    except Exception as e:
        logger.error(f"❌ {ticker} 처리 중 예외 발생: {e}")
        return False


# ==========================================
# 메인 모니터링 루프
# ==========================================

def main():
    """메인 스캐너 루프 - 무한 반복으로 시장 감시"""
    
    logger.info("=" * 60)
    logger.info("🚀 M7 Auto Scanner Started")
    logger.info("=" * 60)
    logger.info(f"📊 감시 대상: {', '.join(TARGET_TICKERS)}")
    logger.info(f"⏱️  체크 주기: {CHECK_INTERVAL}초 ({CHECK_INTERVAL // 60}분)")
    logger.info(f"🔔 알림 쿨다운: {COOLDOWN_PERIOD}초 ({COOLDOWN_PERIOD // 60}분)")
    logger.info("=" * 60)
    logger.info("\n✨ 스캐너 실행 중... (Ctrl+C로 중지)\n")
    
    # 알림 관리자 초기화 (SmartAlertManager)
    smart_alert = utils.SmartAlertManager(cooldown_minutes=COOLDOWN_PERIOD // 60)
    
    # 재시도 카운터 (연속 실패 시 대기 시간 증가)
    consecutive_failures = 0
    max_failures = 5  # 5회 연속 실패 시 경고
    
    try:
        while True:
            logger.info(f"\n🔄 스캔 시작... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            scan_success = False  # 이번 스캔에서 최소 1개라도 성공했는지
            
            for ticker in TARGET_TICKERS:
                result = check_ticker(ticker, smart_alert)
                
                if result or result is False:  # False도 정상 (조건 미충족)
                    scan_success = True
                
                # API 속도 제한 방지 (1초 대기)
                time.sleep(1)
            
            # 스캔 결과 확인
            if scan_success:
                consecutive_failures = 0  # 성공 시 카운터 리셋
            else:
                consecutive_failures += 1
                logger.warning(f"⚠️  스캔 완전 실패 ({consecutive_failures}/{max_failures})")
                
                # 연속 실패 시 경고
                if consecutive_failures >= max_failures:
                    logger.error(f"🚨 {max_failures}회 연속 스캔 실패! 네트워크 상태를 확인하세요.")
                    # 실패 시에도 계속 실행 (재시도)
            
            logger.info(f"\n💤 {CHECK_INTERVAL // 60}분 대기 중...")
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("\n\n🛑 사용자가 스캐너를 중지했습니다.")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"💥 치명적 오류 발생: {e}")
        logger.error("스캐너를 다시 시작해주세요.")


if __name__ == "__main__":
    main()
