"""
M7 Cloud - Supabase Database Manager
Type-safe cloud database integration with comprehensive error handling
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# .env 파일 로드 (환경변수 세팅)
load_dotenv()

class DBManager:
    """
    Supabase 클라우드 DB 연결 및 데이터 관리 클래스
    
    Attributes:
        url (str): Supabase 프로젝트 URL
        key (str): Supabase API 키
        supabase (Client): Supabase 클라이언트 인스턴스
    """
    
    def __init__(self) -> None:
        """
        DBManager 초기화
        
        환경변수에서 SUPABASE_URL과 SUPABASE_KEY를 로드하여 클라이언트를 생성합니다.
        
        Raises:
            ValueError: 환경변수에 필수 값이 없을 경우
        """
        # 환경변수에서 접속 정보 가져오기
        self.url: Optional[str] = os.getenv("SUPABASE_URL")
        self.key: Optional[str] = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("❌ .env 파일에서 SUPABASE_URL 또는 SUPABASE_KEY를 찾을 수 없습니다.")
            
        # 클라이언트 생성 (접속 시도)
        self.supabase: Client = create_client(self.url, self.key)

    def log_signal(
        self, 
        ticker: str, 
        signal_type: str, 
        entry_price: float, 
        filters: Dict[str, str]
    ) -> Optional[Any]:
        """
        신호 발생 시 DB(m7_signals 테이블)에 저장
        
        Args:
            ticker (str): 종목 코드 (예: 'AAPL', 'MSFT')
            signal_type (str): 신호 유형 (예: '강력 매수', '관망')
            entry_price (float): 진입 가격
            filters (Dict[str, str]): 5개 필터 통과 여부
                예: {'market': 'pass', 'chart': 'fail', ...}
        
        Returns:
            Optional[Any]: Supabase 응답 객체. 실패 시 None
        
        Example:
            >>> db = DBManager()
            >>> filters = {'market': 'pass', 'chart': 'pass', 'news': 'pass', 
            ...            'options': 'pass', 'support': 'pass'}
            >>> db.log_signal('AAPL', '강력 매수', 150.25, filters)
        """
        data: Dict[str, Any] = {
            "ticker": ticker,
            "signal_type": signal_type,
            "entry_price": float(entry_price),
            "filters": filters,  # 딕셔너리 형태 그대로 전송 (Supabase가 JSONB로 처리)
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
        test_filters: Dict[str, str] = {"market": "pass", "test": "true"}
        db.log_signal("TEST_BOT", "Connection Check", 100.0, test_filters)
    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")