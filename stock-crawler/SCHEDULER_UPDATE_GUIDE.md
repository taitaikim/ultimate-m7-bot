# 작업 스케줄러 V2 업데이트 가이드

## 🔄 작업 스케줄러를 V2로 변경하는 방법

### 방법 1: 자동 스크립트 사용 (권장)

1. **`setup_scheduler_v2.bat`** 파일을 찾습니다
2. 파일을 **마우스 우클릭**
3. **"관리자 권한으로 실행"** 선택
4. 완료!

이 스크립트는 자동으로:
- ✅ 기존 작업 삭제 (`M7_Auto_Bot`, `Ultimate_M7_Bot`)
- ✅ 새 작업 등록 (`Ultimate_M7_V2_Bot`)
- ✅ 매일 오전 9시 실행 설정

---

### 방법 2: 수동으로 변경

#### 1단계: 기존 작업 삭제
```powershell
# PowerShell을 관리자 권한으로 실행 후
schtasks /Delete /TN "M7_Auto_Bot" /F
schtasks /Delete /TN "Ultimate_M7_Bot" /F
```

#### 2단계: 새 작업 등록
```powershell
schtasks /Create /SC DAILY /TN "Ultimate_M7_V2_Bot" /TR "C:\Users\user\Desktop\Developement\stock-crawler\run_ultimate_v2.bat" /ST 09:00 /F
```

---

### 확인 방법

1. **Win + R** 키 누르기
2. `taskschd.msc` 입력 후 엔터
3. 작업 스케줄러 라이브러리에서 **"Ultimate_M7_V2_Bot"** 찾기
4. 작업 속성 확인:
   - 트리거: 매일 오전 9:00
   - 동작: `run_ultimate_v2.bat` 실행

---

## ⚙️ 실행 시간 변경 (선택사항)

기본 설정은 **매일 오전 9시**입니다. 변경하려면:

### GUI로 변경
1. 작업 스케줄러에서 `Ultimate_M7_V2_Bot` 우클릭
2. "속성" 선택
3. "트리거" 탭에서 시간 수정

### 명령어로 변경
```powershell
# 예: 매일 밤 11시 30분으로 변경
schtasks /Change /TN "Ultimate_M7_V2_Bot" /ST 23:30
```

---

## 🔍 문제 해결

### "액세스가 거부되었습니다"
→ 관리자 권한으로 실행하지 않았습니다. 배치 파일을 우클릭 → 관리자 권한으로 실행

### "작업을 찾을 수 없습니다"
→ 정상입니다. 기존 작업이 없는 경우 나타나는 메시지입니다.

### 작업이 실행되지 않음
1. 작업 스케줄러에서 작업 우클릭 → "실행" 으로 수동 테스트
2. "마지막 실행 결과" 확인
3. 경로가 올바른지 확인: `run_ultimate_v2.bat`의 절대 경로

---

## 📝 기존 버전과의 차이

| 항목 | 기존 (M7_Auto_Bot) | V2 (Ultimate_M7_V2_Bot) |
|------|-------------------|------------------------|
| 실행 파일 | run_ultimate.bat | run_ultimate_v2.bat |
| 실행 시간 | 밤 11:30 | 오전 9:00 |
| 기능 | 기본 분석 | 고급 기술적 분석 |

---

## ✅ 완료 체크리스트

- [ ] `setup_scheduler_v2.bat` 관리자 권한으로 실행
- [ ] 작업 스케줄러에서 `Ultimate_M7_V2_Bot` 확인
- [ ] 기존 작업 (`M7_Auto_Bot`) 삭제 확인
- [ ] 실행 시간 확인 (오전 9:00)
- [ ] 수동 실행 테스트 (작업 우클릭 → 실행)
