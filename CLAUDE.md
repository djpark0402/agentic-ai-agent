# agentic-ai-guardrail

## 아키텍처
풀스택 애플리케이션.

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

### 세션 시작 시 (SessionStart 훅 자동 실행)
1. `feat/pr-develop` 브랜치가 없으면 `develop`에서 자동 생성
2. `feat/pr-develop`에서 `feat/new-promt-YYYYMMDD-HHMMSS` 세션 브랜치 자동 생성
3. 세션 동안 해당 브랜치에서 작업 + Stop 훅으로 자동 커밋

### 프롬프트 제출 시 (UserPromptSubmit 훅 자동 실행)
- 현재 브랜치가 `feat/new-promt-*`가 아니면 자동으로 세션 브랜치를 재생성해 전환
- 세션 중 머지로 브랜치가 삭제된 뒤 다음 프롬프트가 들어와도 Claude가 직접 브랜치를 만들 필요 없음 (훅이 강제로 채움)

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
- **SessionStart 훅**: 세션 시작 시 `feat/pr-develop` → `feat/new-promt-*` 세션 브랜치 자동 생성
- **UserPromptSubmit 훅**: 사용자 프롬프트 제출 시마다 현재 브랜치가 `feat/new-promt-*`가 아니면 자동 재생성 (머지 후 세션 브랜치 삭제 상태에서 다음 프롬프트가 와도 강제 복구)
- **Stop 훅 자동 커밋**: 매 프롬프트 턴이 끝나면 `.claude/hooks/auto-commit.sh`가 실행되어 python lint(ruff→flake8→py_compile 순) 및 frontend lint(eslint→tsc --noEmit 순) 통과 시 변경사항을 로컬에 자동 커밋합니다. lint 실패 시 커밋은 중단됩니다. merge 후 feat/new-promt-* 작업 브랜치는 삭제하세요.
- **원격 push는 항상 사용자 승인 필요**: `git push`는 permission `ask`로 설정되어 있습니다. 로컬 커밋 후 push가 필요하면 반드시 "지금 push 할까요?"라고 사용자에게 먼저 물어보세요.
- **`.env` 파일은 read 전용**: Write/Edit는 permission `deny`로 차단되어 있습니다. `.env` 편집이 필요하면 사용자에게 직접 수정을 요청하세요.
- **merge/PR 시 반드시 사용자 승인**: `feat/pr-develop`는 develop 브랜치에 merge 전 rebase 실행 하십시요.`feat/pr-develop`에 merge 하거나 `develop`에 PR 보낼 때 반드시 사용자에게 먼저 확인을 받으세요.
- **PreToolUse 훅**: `.env` 파일 Edit/Write 시도 시 자동 차단 (exit 2)
- **PostToolUse 훅**: Write/Edit 후 즉시 lint 검사 실행 (`post-lint.sh`)
- **PostCompact 훅**: 컨텍스트 압축 후 핵심 규칙 자동 재주입 (`post-compact.sh`) — 브랜치 규칙, 머지 알림, PR 절차, TDD 등

## Claude 필수 행동 규칙 (절대 생략 금지)

### 1. Stop 훅 머지 알림 수신 시 반드시 질문
- auto-commit.sh에서 커밋 완료 후 "pr-develop에 머지할까요?" systemMessage가 오면, **반드시 사용자에게 머지 여부를 질문할 것**
- 이 알림을 무시하거나 생략하지 말 것

### 2. pr-develop 머지 완료 후 반드시 PR 생성 질문
- 세션 브랜치 → pr-develop 머지가 완료되면, 즉시 **"develop으로 PR 생성할까요?"** 라고 사용자에게 질문할 것
- 머지만 하고 PR 질문을 빠뜨리지 말 것

### 3. 전체 흐름 요약 (매 턴마다 체크)
```
프롬프트 제출 → UserPromptSubmit 훅이 feat/new-promt-* 강제 보장
  → 작업 수행 (Claude는 브랜치 체크/생성 수동으로 하지 않음)
  → Stop 훅: lint 통과 → 자동 커밋
  → "feat/pr-develop에 머지할까요?" 질문
  → 승인 시: 머지 + 세션 브랜치 삭제
  → "develop으로 PR 생성할까요?" 질문
  → 승인 시: rebase → push → PR 생성
```

## 개발 워크플로 (TDD 우선)
- 새 기능이나 버그 수정 시 항상 **실패하는 테스트를 먼저 작성**하고, 해당 테스트가 실제로 실패하는지 확인한 뒤, 그 테스트를 통과시키는 최소한의 실무 코드를 작성해 반영합니다.
- 테스트 없이 실무 코드를 먼저 작성하지 마세요. (red → green → refactor)
- 각 프롬프트 세션에서 코드를 작성한 뒤 python lint를 수동으로도 한 번 확인하고, 통과하면 Stop 훅이 자동으로 커밋을 생성합니다.