import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# .env 파일 로드 (환경변수 세팅)
load_dotenv()

class DBManager:
    """
    Supabase 클라우드 DB 연결 및 데이터 관리 클래스
    """
    def __init__(self):
        # 환경변수에서 접속 정보 가져오기
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("❌ .env 파일에서 SUPABASE_URL 또는 SUPABASE_KEY를 찾을 수 없습니다.")
            
        # 클라이언트 생성 (접속 시도)
        self.supabase: Client = create_client(self.url, self.key)

    def log_signal(self, ticker, signal_type, entry_price, filters):
        """
        신호 발생 시 DB(m7_signals 테이블)에 저장
        """
        data = {
            "ticker": ticker,
            "signal_type": signal_type,
            "entry_price": float(entry_price),
            "filters": filters, # 딕셔너리 형태 그대로 전송 (Supabase가 JSONB로 처리)
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = self.supabase.table("m7_signals").insert(data).execute()
            print(f"✅ [Cloud DB] {ticker} 신호 저장 성공!")
            return response
        except Exception as e:
            print(f"❌ [Cloud DB] 저장 실패: {e}")
            return None

# --- 연결 테스트 (이 파일을 직접 실행했을 때만 작동) ---
if __name__ == "__main__":
    print("📡 Supabase 접속 테스트 중...")
    try:
        db = DBManager()
        # 가짜 데이터로 테스트 전송
        test_filters = {"market": "pass", "test": "true"}
        db.log_signal("TEST_BOT", "Connection Check", 100.0, test_filters)
    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")