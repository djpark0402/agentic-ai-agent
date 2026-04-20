# agentic-ai-guardrail

## 아키텍처
풀스택 애플리케이션 — Solar LLM 채팅 + 대화 영속화 + function calling 도구.
- **Backend**: FastAPI(Python 3.12) / SQLModel / Alembic / asyncpg
- **Frontend**: React 18 + TypeScript + Vite (nginx로 배포 시 SPA + `/api` 프록시)
- **DB**: PostgreSQL 16 (대화·메시지 영속화, 슬라이딩 윈도우 20턴)
- **LLM 연동**: OpenAI 호환 `/v1/chat/completions`, HMAC-SHA256 서명 헤더(`X-API-Key/X-Timestamp/X-Nonce/X-Signature`)
- **도구**: `backend/app/tools.py`에 로컬 function 등록 (현재 `get_top_stocks` — FinanceDataReader)
- **도커**: frontend(54084) / backend(54085) / postgres(54086) — `docker compose up -d --build`

## Git 워크플로
- main/master 브랜치에 직접 commit/push 금지
- 컨벤셔널 커밋 사용: feat, fix, docs, refactor, test, chore
- PR 체크리스트: 테스트 통과, lint 통과, 리뷰어 지정
- .env 파일이나 민감 정보는 절대 커밋 금지
- Bash 명령어를 &&, ;, | 로 체이닝하지 말 것 — 항상 개별 도구 호출 사용
- 커밋 형식: `feat: 메시지` / `fix: 메시지` / `docs:` / `refactor:` / `test:` / `chore:`
- 모든 커밋에 `Co-Authored-By: Claude <noreply@anthropic.com>` 추가
- **커밋 메시지는 반드시 한글로 작성할 것!**

## 브랜치 전략
```
main (프로덕션)
 └── develop (개발 통합)
      └── feat/pr-develop (PR 준비용 통합 브랜치)
           └── feat/new-promt-YYYYMMDD-HHMMSS (매 세션 작업 브랜치, 자동 생성, pr-develop에 merge 시 반드시 사용자 승인 필요, merge후 삭제)
                ├── feat/기능설명 (기능별 분리 브랜치)
                ├── fix/버그설명
                ├── docs/문서설명
                ├── refactor/리팩토링설명
                ├── test/테스트설명
                └── chore/설정설명
```

### 세션 브랜치 생성 정책 (지연 생성)
- <span style="color:red">**SessionStart**</span> 훅 (`.claude/hooks/session-start.sh`) — CLI 최초 기동 시 1회
  - `feat/pr-develop` 없으면 `develop`에서 생성
  - 첫 세션 브랜치(`feat/new-promt-YYYYMMDD-HHMMSS`) 선제 생성 (탐색/질문만 해도 안전한 시작점 확보)
- <span style="color:red">**PreToolUse**</span> 훅 (`.claude/hooks/check-branch.sh`) — **실제 Edit/Write 직전 지연 생성**
  - 현재 `feat/new-promt-*` → 그대로 허용 (exit 0)
  - 현재 `feat/pr-develop` → **새 세션 브랜치 자동 생성 후 전환 → Edit 허용**
  - 현재 `main` / `master` / `develop` → 차단 (exit 2, 사용자가 pr-develop으로 이동해야 함)
  - `.claude/` 경로 편집은 어디서든 허용 (훅·설정 변경 목적)

**핵심**: 머지로 세션 브랜치가 사라진 뒤 사용자가 질문·탐색만 해도 빈 브랜치를 만들지 않고, 실제 파일 수정이 필요한 순간에만 세션 브랜치가 생성됩니다. Claude는 브랜치 체크/생성을 수동으로 하지 않음.

### 세션 종료 / 작업 완료 시 (Claude 수동 수행, 사용자 승인 필요)
1. 세션 브랜치의 커밋을 분석하여 작업 유형별로 분리
2. 유형별 브랜치 생성: `feat/backend-auth`, `docs/api-spec`, `fix/login-error` 등
3. 각 브랜치를 `feat/pr-develop`에 merge → **반드시 사용자에게 확인** → merge gn 각 브랜치 삭제 (feat/pr-develop 브랜치는 유지)
4. `feat/pr-develop` → `develop`으로 PR 생성 → **반드시 사용자에게 확인** → feat/pr-develop 브랜치는 PR 생성전 반드시 develop브랜치를 기준으로 rebase 시키고 PR 생성 함(소스 충돌 방지)
5. PR 생성 시 `.github/PULL_REQUEST_TEMPLATE.md` 템플릿 사용

### 브랜치 접두사 규칙
- `feat/` : 새 기능
- `fix/` : 버그 수정
- `docs/` : 문서 작업
- `style/` : 코드 포맷팅
- `refactor/` : 리팩토링
- `test/` : 테스트
- `chore/` : 빌드/설정
- `perf/` : 성능 개선
- `ci/` : CI/CD
- `build/` : 빌드 시스템

## 자동화 정책 (hooks + permissions)

### 브랜치 관리
- <span style="color:red">**SessionStart**</span> 훅 (`session-start.sh`): CLI 시작 시 1회 — pr-develop 보장 + 초기 세션 브랜치 생성
- <span style="color:red">**PreToolUse**</span> 훅 (`check-branch.sh`): Edit/Write 직전 — pr-develop이면 세션 브랜치 자동 생성, main/master/develop이면 exit 2 차단 (지연 생성 전략)

### 커밋/머지/푸시
- <span style="color:red">**Stop**</span> 훅 (`auto-commit.sh`): 매 프롬프트 턴 종료 시 lint(ruff→flake8→py_compile, eslint→tsc --noEmit) 통과 후 자동 커밋. lint 실패 시 커밋 중단. 커밋 완료 후 "feat/pr-develop에 머지할까요?" 질문을 Claude에게 강제.
- <span style="color:red">**PostToolUse**</span> 훅 (`check-merge.sh`): `git merge` 감지 시 "develop으로 PR 생성할까요?" 질문 강제.
- <span style="color:red">**PostToolUse**</span> 훅 (`post-lint.sh`): Write/Edit 직후 즉시 lint 검사.
- **원격 push는 항상 사용자 승인 필요** — `git push`는 permission `ask`. 푸시 전에 "지금 push 할까요?" 질문.
- **merge/PR은 항상 사용자 승인** — pr-develop에 머지하거나 develop으로 PR 생성 전 반드시 확인. PR 생성 전 pr-develop은 develop 기준으로 rebase 필수 (충돌 방지).

### 보안
- **`.env`는 read 전용** — `Edit(**/.env)` / `Write(**/.env)`는 permission `deny`. 수정 필요 시 사용자에게 직접 요청.
- <span style="color:red">**PreToolUse**</span> 보조 차단: `.env` 경로 Edit/Write 시 인라인 훅으로도 exit 2.

### 컨텍스트 관리
- <span style="color:red">**PostCompact**</span> 훅 (`post-compact.sh`): 컨텍스트 압축 후 핵심 규칙 재주입 (브랜치·머지·PR·TDD·한글 커밋 등).

## Claude 필수 행동 규칙 (절대 생략 금지)

### 1. <span style="color:red">**Stop**</span> 훅 머지 알림 수신 시 반드시 질문
- auto-commit.sh에서 커밋 완료 후 "pr-develop에 머지할까요?" systemMessage가 오면, **반드시 사용자에게 머지 여부를 질문할 것**
- 이 알림을 무시하거나 생략하지 말 것

### 2. pr-develop 머지 완료 후 반드시 PR 생성 질문
- 세션 브랜치 → pr-develop 머지가 완료되면, 즉시 **"develop으로 PR 생성할까요?"** 라고 사용자에게 질문할 것
- 머지만 하고 PR 질문을 빠뜨리지 말 것

### 3. 전체 흐름 요약 (매 턴마다 체크)
```
프롬프트 제출
  ↓
(탐색/질문만이면 브랜치 변화 없음 — 빈 세션 브랜치 생성 안 함)
  ↓
실제 Edit/Write 발생 시 PreToolUse 훅이 세션 브랜치 자동 생성/보장
  ↓
작업 수행 → Stop 훅: lint 통과 → 자동 커밋
  ↓
"feat/pr-develop에 머지할까요?" 질문 → 승인 시 머지 + 세션 브랜치 삭제
  ↓
"develop으로 PR 생성할까요?" 질문 → 승인 시 rebase → push → PR 생성
```

## 개발 워크플로 (TDD 우선)
- 새 기능이나 버그 수정 시 항상 **실패하는 테스트를 먼저 작성**하고, 해당 테스트가 실제로 실패하는지 확인한 뒤, 그 테스트를 통과시키는 최소한의 실무 코드를 작성해 반영합니다.
- 테스트 없이 실무 코드를 먼저 작성하지 마세요. (red → green → refactor)
- 각 프롬프트 세션에서 코드를 작성한 뒤 python lint를 수동으로도 한 번 확인하고, 통과하면 <span style="color:red">**Stop**</span> 훅이 자동으로 커밋을 생성합니다.
- Backend 테스트: `cd backend && .venv/bin/pytest` (conftest의 `DATABASE_URL`은 로컬 postgres 사용)
- Frontend 타입체크: `cd frontend && npx tsc --noEmit`

## 로컬 function-calling 도구
`backend/app/tools.py`에 등록된 도구는 LLM이 `tool_choice:auto`로 자동 호출 가능.
- **새 도구 추가 절차:**
  1. `tools.py`에 async 함수 구현
  2. `TOOL_SCHEMAS`에 OpenAI JSON Schema 형식으로 등록
  3. `TOOL_FUNCTIONS`에 name → callable 매핑 추가
- **트리거**: `main.py`의 키워드 조건 (`코스피`/`코스닥`/`주식`/`시가총액`/`주가` 등) 충족 시 tools 주입. 조건 없이 항상 주입하려면 `main.py`의 tools_schema 분기 제거.
- 구현 예: `get_top_stocks(market, by, n)` — FinanceDataReader 기반 KOSPI/KOSDAQ 상위 종목