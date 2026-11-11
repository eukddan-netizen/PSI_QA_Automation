# 07. 지원&문의 (`main_07`)

- **대분류**: 보안점검 메인 탭
- **중분류**: 지원&문의
- **엑셀 범위**: 35행
- **실행 명령**: `.\run main 7` (또는 `pytest -m main_07 -s`)

## 테스트 개요
웹 관리자 콘솔(https://192.168.4.151)의 환경설정(`/manageConfig`) > 보안점검 탭에서 지정하는 '문의처' 설정이 내PC보안점검 클라이언트 메인 화면 좌측 하단의 `[지원&문의]` 우측 텍스트 문구로 실시간 동기화되는지 검증하고, 검증 종료 후 원래 문구("전산팀")로 안전하게 롤백되는지 확인합니다.

## 테스트 명세
| 행 | 함수명 | 항목 | 검증 세부 내용 | 기대 결과 |
| :-: | :--- | :--- | :--- | :--- |
| 35 | `test_main_support_inquiry_text_sync` | 지원&문의 문구 및 환경설정 연동/롤백 검증 | 1. 관리자 콘솔 `/manageConfig` > 보안점검 탭 접속<br>2. 하단 '문의처' input에 "QA팀" 입력 후 '저장' 및 모달 확인<br>3. 보안점검 클라이언트 프로그램 재실행<br>4. 하단 지원&문의 문구가 "QA팀"으로 변경되었는지 확인<br>5. 관리자 콘솔에서 다시 "전산팀"으로 원복 저장<br>6. 클라이언트 재실행 후 "전산팀" 원복 확인 | - 서버 환경설정 문의처 변경 시 클라이언트 메인 화면 좌측 하단 문구에 즉시 반영<br>- 검증 완료 후 기존 문구("전산팀")로 100% 원복 및 클라이언트 복구 확인 |

## 관련 페이지 객체
- [AdminManageConfigPage](file:///d:/psi_automation/pages/admin_manage_config_page.py):
  - `goto_manage_config()`: `/manageConfig` 환경설정 페이지 이동
  - `select_tab(tab_name)`: 5개 탭('에이전트', '보안점검', '패치', '다운로드', '배포서버') 전환
  - `get_contact_text()`: '문의처' 행 input 텍스트 조회
  - `set_contact_text(text)`: '문의처' 행 input 텍스트 입력
  - `save_config()`: 하단 '저장' 버튼 클릭 및 완료 모달 처리
- [MainPage](file:///d:/psi_automation/pages/main_page.py):
  - `get_support_inquiry_text()`: 메인 화면 좌측 하단 '지원&문의' 옆 안내 문구 텍스트 조회

