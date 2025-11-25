import os
import sys
import asyncio
from dotenv import load_dotenv
from telegram import Bot
from supabase import create_client
import openai

# Load environment variables
load_dotenv()

def check_env_vars():
    required_vars = [
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
        "OPENAI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY"
    ]
    missing = []
    print("🔍 환경 변수 확인 중...")
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
            print(f"❌ {var} 없음")
        else:
            masked = value[:4] + "*" * 4 if len(value) > 4 else "****"
            print(f"✅ {var} 확인됨 ({masked})")
    
    return len(missing) == 0

async def check_telegram():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        return False
    
    print("\n📨 텔레그램 연결 확인 중...")
    try:
        bot = Bot(token=token)
        me = await bot.get_me()
        print(f"✅ 텔레그램 연결 성공: {me.first_name} (@{me.username})")
        return True
    except Exception as e:
        print(f"❌ 텔레그램 연결 실패: {e}")
        return False

def check_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return False
        
    print("\n🗄️ Supabase DB 연결 확인 중...")
    try:
        supabase = create_client(url, key)
        # Try to select 1 row from m7_signals just to check connection
        # If table is empty it returns empty list, which is fine (no error)
        response = supabase.table("m7_signals").select("*", count="exact").limit(1).execute()
        print(f"✅ Supabase 연결 성공 (테이블 접근 가능)")
        return True
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False

def check_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False
        
    print("\n🧠 OpenAI API 연결 확인 중...")
    try:
        client = openai.OpenAI(api_key=api_key)
        # Just list models to verify key
        client.models.list()
        print("✅ OpenAI 연결 성공")
        return True
    except Exception as e:
        print(f"❌ OpenAI 연결 실패: {e}")
        return False

async def main():
    print("🚀 시스템 상태 점검 시작...\n")
    
    env_ok = check_env_vars()
    if not env_ok:
        print("\n⚠️ 일부 환경 변수가 누락되었습니다. .env 파일을 확인해주세요.")
    
    tg_ok = await check_telegram()
    db_ok = check_supabase()
    ai_ok = check_openai()
    
    print("\n" + "="*30)
    print("📊 점검 결과 요약")
    print("="*30)
    print(f"환경 변수: {'✅ 정상' if env_ok else '❌ 확인 필요'}")
    print(f"텔레그램: {'✅ 정상' if tg_ok else '❌ 실패'}")
    print(f"데이터베이스: {'✅ 정상' if db_ok else '❌ 실패'}")
    print(f"OpenAI: {'✅ 정상' if ai_ok else '❌ 실패'}")
    print("="*30)

if __name__ == "__main__":
    asyncio.run(main())
