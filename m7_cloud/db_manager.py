"""
M7 Cloud - Supabase Database Manager
Type-safe cloud database integration with comprehensive error handling
"""

import os
import streamlit as st
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# .env 파일 로드 (로컬 개발 환경용)
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
        
        우선순위:
        1. Streamlit Cloud Secrets (배포 환경)
        2. Local Environment Variables (로컬 개발 환경)
        
        Raises:
            ValueError: 접속 정보를 어디서도 찾을 수 없을 경우
        """
        self.url: Optional[str] = None
        self.key: Optional[str] = None

        # 1. Streamlit Cloud Secrets 시도
        try:
            if hasattr(st, "secrets") and "SUPABASE_URL" in st.secrets:
                self.url = st.secrets["SUPABASE_URL"]
                self.key = st.secrets["SUPABASE_KEY"]
        except Exception:
            pass
        
        # 2. 로컬 환경변수(.env) 시도 (Secrets가 없거나 실패한 경우)
        if not self.url or not self.key:
            self.url = os.getenv("SUPABASE_URL")
            self.key = os.getenv("SUPABASE_KEY")
        
        # 3. 검증
        if not self.url or not self.key:
            raise ValueError(
                "❌ .env 파일 또는 Streamlit Secrets에서 접속 정보를 찾을 수 없습니다."
            )
            
        # 클라이언트 생성
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
            ticker (str): 종목 코드 (예: 'AAPL')
            signal_type (str): 신호 유형 (예: '강력 매수')
            entry_price (float): 진입 가격
            filters (Dict[str, str]): 필터 통과 여부
        
        Returns:
            Optional[Any]: Supabase 응답 객체. 실패 시 None
        """
        data: Dict[str, Any] = {
            "ticker": ticker,
            "signal_type": signal_type,
            "entry_price": float(entry_price),
            "filters": filters,
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
        # 가짜 데이터로 테스트 전송 (연결 확인용)
        test_filters: Dict[str, str] = {"market": "pass", "test": "true"}
        db.log_signal("TEST_BOT", "Cloud Connection Check", 100.0, test_filters)
        print("✅ 연결 및 데이터 전송 성공!")
    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")