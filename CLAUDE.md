# agentic-ai-guardrail

## 아키텍처
풀스택 애플리케이션 — Solar LLM 채팅 + 대화 영속화 + function calling 도구.
- **Backend**: FastAPI(Python 3.12) / SQLModel / Alembic / asyncpg
- **Frontend**: React 18 + TypeScript + Vite (nginx로 배포 시 SPA + `/api` 프록시)
- **DB**: PostgreSQL 16 (대화·메시지 영속화, 슬라이딩 윈도우 20턴)
- **LLM 연동**: OpenAI 호환 `/v1/chat/completions`, HMAC-SHA256 서명 헤더(`X-API-Key/X-Timestamp/X-Nonce/X-Signature`)
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
           └── feat/new-prompt-YYYYMMDD-HHMMSS (세션 브랜치 — 항상 1개만 유지, 자동 생성/재사용, pr-develop에 1회 머지 후 삭제)
```

- **하위 분리 브랜치(feat/..., docs/..., fix/... 등)를 만들지 않는다.** 세션 브랜치를 유형별로 쪼개지 않고 그대로 `feat/pr-develop`에 머지한다.
- `feat/new-prompt-*`는 **항상 1개만 유지** — 기존 세션 브랜치가 있으면 SessionStart / PreToolUse / Stop 훅이 모두 그걸 재사용하고, 없을 때만 새로 생성한다.

### 세션 브랜치 생성 정책 (순수 지연 생성)
세션 브랜치(`feat/new-prompt-YYYYMMDD-HHMMSS`)는 **실제로 필요한 이벤트가 발생할 때만** 만들어집니다. SessionStart는 세션 브랜치를 **만들지 않습니다**.

-  훅 (`session-start.sh`) — CLI 최초 기동 시 1회
  - `feat/pr-develop`이 없으면 `develop`에서 생성. `develop`이 없으면 `main` → `master` 순으로 기준 브랜치를 찾아 `develop`부터 자동 생성
  - 기존 `feat/new-prompt-*` 세션 브랜치가 있으면 체크아웃하여 **이어서 작업** (2개 이상이면 최신 하나만 남기고 자동 정리)
  - 기존 세션 브랜치가 없으면 `feat/pr-develop`으로만 이동 (Edit 시 지연 생성에 맡김)

- 훅 (`check-branch.sh`) — **Edit/Write 직전 지연 생성/재사용 (주 경로)**
  - `feat/new-prompt-*` → 그대로 허용
  - `feat/pr-develop` → 기존 `feat/new-prompt-*`가 있으면 체크아웃해서 **이어서 작업**, 없을 때만 새 세션 브랜치 생성
  - `main` / `master` / `develop` → exit 2 차단
  - `.claude/` 경로는 어디서든 허용 (훅·설정 변경 목적)

- 훅 (`auto-commit.sh`) — **커밋 직전 안전망**
  - 커밋 시점에 `feat/pr-develop`에 변경사항이 있으면 (Bash 기반 파일 수정 / `.claude/` 편집으로 PreToolUse를 우회한 경우) 기존 `feat/new-prompt-*`가 있으면 그리로 체크아웃, 없으면 새로 생성한 뒤 커밋
  - 즉 "pr-develop에 직접 커밋되는" 경우가 없고, 세션 브랜치는 항상 1개만 유지됨

**핵심**: 질문·탐색만 하는 턴은 브랜치 변화 0. 실제 파일 수정이 발생해야만 세션 브랜치가 생성됩니다. Claude는 브랜치 체크/생성을 수동으로 하지 않음.

### 세션 종료 / 작업 완료 시 (Claude 수동 수행, 사용자 승인 필요)
1. **세션 브랜치를 유형별로 쪼개지 않는다.** 세션 브랜치(`feat/new-prompt-*`)를 통째로 `feat/pr-develop`에 **`--no-ff`로 1회 머지** → **반드시 사용자에게 확인** → 머지 후 세션 브랜치 삭제 (feat/pr-develop 브랜치는 유지)
2. `feat/pr-develop` → `develop`으로 PR 생성 → **반드시 사용자에게 확인** → feat/pr-develop 브랜치는 PR 생성 전 반드시 develop 기준으로 rebase (소스 충돌 방지)
3. PR 생성 시 `.github/PULL_REQUEST_TEMPLATE.md` 템플릿 사용

### 커밋 타입 접두사 규칙 (커밋 메시지 · 컨벤셔널 커밋용)
> 아래 접두사는 **커밋 메시지 타입**에만 쓰며, 브랜치 이름에는 쓰지 않는다 (브랜치는 `feat/pr-develop`, `feat/new-prompt-*`, `develop`, `main`만 존재).

- `feat:` : 새 기능
- `fix:` : 버그 수정
- `docs:` : 문서 작업
- `style:` : 코드 포맷팅
- `refactor:` : 리팩토링
- `test:` : 테스트
- `chore:` : 빌드/설정
- `perf:` : 성능 개선
- `ci:` : CI/CD
- `build:` : 빌드 시스템

## 자동화 정책 (hooks + permissions)

### 브랜치 관리
- 훅 (`session-start.sh`): CLI 시작 시 1회 — pr-develop 보장 + 초기 세션 브랜치 생성
- **PreToolUse** 훅 (`check-branch.sh`): Edit/Write 직전 — pr-develop이면 세션 브랜치 자동 생성, main/master/develop이면 exit 2 차단 (지연 생성 전략)

### 커밋/머지/푸시
- **Stop** 훅 (`auto-commit.sh`): 매 프롬프트 턴 종료 시 lint(ruff→flake8→py_compile, eslint→tsc --noEmit) 통과 후 자동 커밋. lint 실패 시 커밋 중단. 커밋 완료 후 "feat/pr-develop에 머지할까요?" 질문을 Claude에게 강제.
- **PostToolUse** 훅 (`check-merge.sh`): `git merge` 감지 시 "develop으로 PR 생성할까요?" 질문 강제.
- **PostToolUse** 훅 (`post-lint.sh`): Write/Edit 직후 즉시 lint 검사.
- **원격 push는 항상 사용자 승인 필요** — `git push`는 permission `ask`. 푸시 전에 "지금 push 할까요?" 질문.
- **merge/PR은 항상 사용자 승인** — pr-develop에 머지하거나 develop으로 PR 생성 전 반드시 확인. PR 생성 전 pr-develop은 develop 기준으로 rebase 필수 (충돌 방지).

### 보안
- **`.env`는 read 전용** — `Edit(**/.env)` / `Write(**/.env)`는 permission `deny`. 수정 필요 시 사용자에게 직접 요청.
- **PreToolUse** 보조 차단: `.env` 경로 Edit/Write 시 인라인 훅으로도 exit 2.

### 컨텍스트 관리
- **PostCompact** 훅 (`post-compact.sh`): 컨텍스트 압축 후 핵심 규칙 재주입 (브랜치·머지·PR·TDD·한글 커밋 등).

## Claude 필수 행동 규칙 (절대 생략 금지)

### 1. **Stop** 훅 머지 알림 수신 시 반드시 질문
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
- 각 프롬프트 세션에서 코드를 작성한 뒤 python lint를 수동으로도 한 번 확인하고, 통과하면 **Stop** 훅이 자동으로 커밋을 생성합니다.
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