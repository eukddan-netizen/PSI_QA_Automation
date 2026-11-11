# 05. 암호 안전성 검사 (`main_05`)

- **대분류**: 보안점검 메인 탭
- **중분류**: 암호 안전성 검사
- **엑셀 범위**: 32행
- **실행 명령**: `.\run main 5` (또는 `pytest -m main_05 -s`)

## 테스트 개요
메인 화면 우측의 '암호 안전성 검사' 카드를 클릭하여 호출되는 모달 팝업 창의 오탈자, 눈 아이콘(보임/숨김 토글), 한글 입력 시 에러 문구, 5단계 기준(9자 이상, 대/소문자, 숫자, 특수문자) 충족에 따른 게이지 바(20%~100%) 및 등급(약함/보통/강함) 변화를 단일 세션에서 전수 검증합니다.

## 테스트 명세
| 단계 | 함수명 | 항목 | 검증 세부 내용 | 기대 결과 |
| :-: | :--- | :--- | :--- | :--- |
| Step 1 | `test_step1_password_modal_open_and_spelling` | 모달 오픈 및 오탈자 검증 | 모달 헤더, 인풋 placeholder, 5개 기준 텍스트 및 초기 '약함' 상태 검증 | - 타이틀 '암호 안전성 검사'<br>- 5개 기준('9자 이상', '대문자 포함', '소문자 포함', '숫자 포함', '특수문자 포함') 오탈자 없음<br>- 초기 등급 '약함' 및 0% 수준 게이지 바 확인 |
| Step 2 | `test_step2_password_visibility_toggle` | 눈 아이콘 보임/숨김 토글 | 눈 아이콘(pw-toggle) 버튼 클릭에 따른 비밀번호 원문 표시/마스킹 전환 | - 1차 클릭: 비밀번호 보이는 상태(Hide password)로 전환<br>- 2차 클릭: 원래 숨김 상태(Show password)로 원복 |
| Step 3 | `test_step3_korean_input_warning_message` | 한글 입력 시 경고 문구 | 비밀번호 보이는 상태에서 한글 입력 시 에러 문구 검출 | - '입력할 수 없는 문자가 포함되어 있습니다.' 빨간색 경고 출력<br>- 정상 영문 재입력 시 경고 자동 해제 |
| Step 4 | `test_step4_five_criteria_and_gauge_bar_progression` | 5단계 기준 및 게이지 바 증가 | 1~5개 조건 순차 충족 시 체크 표시(✓), 일자 바 너비(20%~100%), 색상(주황/초록), 등급(약함/보통/강함) 전수 검증 | - 1개(20%), 2개(40%), 3개(60%): 주황색 바 및 '약함'<br>- 4개(80%, 9자+3문자 조합): 초록색 바 및 '보통'<br>- 5개(100%): 초록색 바 및 '강함' |
| Step 5 | `test_step5_password_modal_close` | 모달 닫기 검증 | 하단 '닫기' 버튼 클릭에 따른 모달 종료 확인 | - 모달이 정상 종료되고 메인 화면 복귀 |

## 관련 페이지 객체
- [PasswordSafetyModalPage](file:///d:/psi_automation/pages/password_safety_modal_page.py): 암호 안전성 검사 모달 전용 제어기
- [MainPage](file:///d:/psi_automation/pages/main_page.py): 메인 대시보드 `click_password_safety_card()` 지원
