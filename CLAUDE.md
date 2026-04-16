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

## 자동화 정책 (hooks + permissions)
- **Stop 훅 자동 커밋**: 매 프롬프트 턴이 끝나면 `.claude/hooks/auto-commit.sh`가 실행되어 python lint(ruff→flake8→py_compile 순) 통과 시 변경사항을 로컬에 자동 커밋합니다. lint 실패 시 커밋은 중단됩니다.
- **원격 push는 항상 사용자 승인 필요**: `git push`는 permission `ask`로 설정되어 있습니다. 로컬 커밋 후 push가 필요하면 반드시 "지금 push 할까요?"라고 사용자에게 먼저 물어보세요.
- **`.env` 파일은 read 전용**: Write/Edit는 permission `deny`로 차단되어 있습니다. `.env` 편집이 필요하면 사용자에게 직접 수정을 요청하세요.

## 개발 워크플로 (TDD 우선)
- 새 기능이나 버그 수정 시 항상 **실패하는 테스트를 먼저 작성**하고, 해당 테스트가 실제로 실패하는지 확인한 뒤, 그 테스트를 통과시키는 최소한의 실무 코드를 작성해 반영합니다.
- 테스트 없이 실무 코드를 먼저 작성하지 마세요. (red → green → refactor)
- 각 프롬프트 세션에서 코드를 작성한 뒤 python lint를 수동으로도 한 번 확인하고, 통과하면 Stop 훅이 자동으로 커밋을 생성합니다.