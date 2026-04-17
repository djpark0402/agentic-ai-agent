#!/usr/bin/env bash
# ============================================================================
# PreToolUse Hook — 보호 브랜치에서 파일 수정 차단
# 트리거: PreToolUse (matcher: "Edit|Write")
# develop, pr-develop, main에서 직접 파일 수정 시 차단
# feat/new-promt-* 브랜치에서만 작업 허용
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

cd "${CWD:-$(git rev-parse --show-toplevel 2>/dev/null)}" || exit 0

BRANCH=$(git branch --show-current 2>/dev/null)

# .claude/ 설정 파일은 어디서든 수정 허용 (hooks 설정 변경 등)
if echo "$FILE_PATH" | grep -q '\.claude/'; then
  exit 0
fi

# 보호 브랜치 목록
case "$BRANCH" in
  main|master|develop|feat/pr-develop)
    echo "보호 브랜치($BRANCH)에서 직접 파일을 수정할 수 없습니다. feat/new-promt-* 세션 브랜치를 생성한 후 작업하세요." >&2
    exit 2
    ;;
esac

exit 0
