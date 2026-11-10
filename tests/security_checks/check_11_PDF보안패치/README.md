# 11. PDF 프로그램 최신 보안 패치 점검 (`check_11_PDF보안패치`)

- **점검 번호**: 11번
- **점검 제목**: 11. PDF 프로그램 최신 보안 패치 점검
- **앱 UI 키워드**: `PDF 프로그램 최신 보안 패치`
- **자동화 난이도**: Tier B (외부 프로그램 설치 또는 PowerShell/권한/재부팅 환경 구성 필요)
- **분류 근거**: Chocolatey 등을 이용한 Adobe Acrobat Reader 구버전 설치 및 업데이트 환경 구성이 필요함
- **구현 상태**: `skeleton`
- **pytest 마커**: `check11`, `tier_b`

## 1. 점검 대상 및 판정 기준 / 안내 문구
- **점검 대상**: PDF 프로그램 최신 보안 패치 점검
- [adobe reader 미설치] 안전 및 Adobe Acrobat Reader가 설치되지 않았습니다.
- [adobe reader 최신버전] 안전 및 최신상태 문구 + 버전 정보
- [기존 reader 삭제] 취약 및 Adobe Acrobat Reader의 업데이트가 있습니다. + 현재 버전과 최신 버전 정보 제공
- [adobe reader 구버전] 안전 및 최신 버전으로 업데이트

## 2. 상태를 만드는 방법 (OS / 환경 설정)
- (adobe reader 미설치) 점검 진행
- (기존 reader 삭제) <powershell 관리자 권한> Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1')) // choco 설치 / 이미 설치된 경우 스킵 choco install adobereader --version=2025.1.20577 // reader 구버전 설치 https://unused.tistory.com/entry/Adobe-Acrobat-Reader-DC-%EA%B5%AC%EB%B2%84%EC%A0%84-%EC%84%A4%EC%B9%98 점검 진행

## 3. 조치 시 기대 동작
- **조치 진행** → 안전 및 최신 버전으로 업데이트
- 공통 사항: 취약 상태에서 안전 상태로 전환 시 상단 취약 건수 감소 및 서버 설정 점수 가감 일치 확인
