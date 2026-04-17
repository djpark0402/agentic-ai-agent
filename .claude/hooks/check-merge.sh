#!/usr/bin/env bash
# ============================================================================
# PostToolUse Hook — git merge 후 PR 생성 질문 강제
# 트리거: PostToolUse (matcher: "Bash")
# pr-develop에서 머지가 감지되면 Claude에게 PR 질문을 강제
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

cd "${CWD:-$(git rev-parse --show-toplevel 2>/dev/null)}" || exit 0

# git merge 명령이 아니면 무시
echo "$COMMAND" | grep -q 'git merge' || exit 0

BRANCH=$(git branch --show-current 2>/dev/null)

# pr-develop에서 머지가 실행된 경우 PR 질문 강제
if [ "$BRANCH" = "feat/pr-develop" ]; then
  jq -n '{
    "decision": "block",
    "reason": "feat/pr-develop에 머지 완료. 사용자에게 반드시 develop으로 PR 생성할까요? 라고 물어보세요."
  }'
  exit 0
fi

exit 0
