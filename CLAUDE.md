# agentic-ai-guardrail

## Architecture
Full-stack application.

## Git Workflow
- Never push directly to main/master
- Use conventional commits: feat, fix, docs, refactor, test, chore
- PR checklist: tests pass, lint pass, reviewer assigned
- Never commit .env files or sensitive information
- Never chain Bash commands with &&, ;, or | — always use separate tool calls
- Commit format: `feat: msg` / `fix: msg` / `docs:` / `refactor:` / `test:` / `chore:`
- Add `Co-Authored-By: Claude <noreply@anthropic.com>` to all commits
- **커밋 메시지는 반드시 한글로 작성해주세요!**
- **Please make sure to write the commit messages in Korean!**

## 브랜치 전략
```
main (프로덕션)
 └── develop (개발 통합)
      └── feat/pr-develop (PR 준비용 통합 브랜치)
           └── feat/session-YYYYMMDD-HHMMSS (세션 작업 브랜치, 자동 생성)
                ├── feat/기능설명 (기능별 분리 브랜치)
                ├── fix/버그설명
                ├── docs/문서설명
                ├── refactor/리팩토링설명
                ├── test/테스트설명
                └── chore/설정설명
```

### 세션 시작 시 (SessionStart 훅 자동 실행)
1. `feat/pr-develop` 브랜치가 없으면 `develop`에서 자동 생성
2. `feat/pr-develop`에서 `feat/session-YYYYMMDD-HHMMSS` 세션 브랜치 자동 생성
3. 세션 동안 해당 브랜치에서 작업 + Stop 훅으로 자동 커밋

### 세션 종료 / 작업 완료 시 (Claude 수동 수행, 사용자 승인 필요)
1. 세션 브랜치의 커밋을 분석하여 작업 유형별로 분리
2. 유형별 브랜치 생성: `feat/backend-auth`, `docs/api-spec`, `fix/login-error` 등
3. 각 브랜치를 `feat/pr-develop`에 merge → **반드시 사용자에게 확인**
4. `feat/pr-develop` → `develop`으로 PR 생성 → **반드시 사용자에게 확인**
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
- **SessionStart 훅**: 세션 시작 시 `feat/pr-develop` → `feat/session-*` 세션 브랜치 자동 생성
- **Stop 훅 자동 커밋**: 매 프롬프트 턴이 끝나면 `.claude/hooks/auto-commit.sh`가 실행되어 python lint(ruff→flake8→py_compile 순) 통과 시 변경사항을 로컬에 자동 커밋합니다. lint 실패 시 커밋은 중단됩니다.
- **원격 push는 항상 사용자 승인 필요**: `git push`는 permission `ask`로 설정되어 있습니다. 로컬 커밋 후 push가 필요하면 반드시 "지금 push 할까요?"라고 사용자에게 먼저 물어보세요.
- **`.env` 파일은 read 전용**: Write/Edit는 permission `deny`로 차단되어 있습니다. `.env` 편집이 필요하면 사용자에게 직접 수정을 요청하세요.
- **merge/PR 시 반드시 사용자 승인**: `feat/pr-develop`에 merge 하거나 `develop`에 PR 보낼 때 반드시 사용자에게 먼저 확인을 받으세요.

## 개발 워크플로 (TDD 우선)
- 새 기능이나 버그 수정 시 항상 **실패하는 테스트를 먼저 작성**하고, 해당 테스트가 실제로 실패하는지 확인한 뒤, 그 테스트를 통과시키는 최소한의 실무 코드를 작성해 반영합니다.
- 테스트 없이 실무 코드를 먼저 작성하지 마세요. (red → green → refactor)
- 각 프롬프트 세션에서 코드를 작성한 뒤 python lint를 수동으로도 한 번 확인하고, 통과하면 Stop 훅이 자동으로 커밋을 생성합니다.