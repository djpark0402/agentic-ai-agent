#!/usr/bin/env bash
# ============================================================================
# UserPromptSubmit Hook — 프롬프트 제출 시 세션 브랜치 자동 보장
# 트리거: UserPromptSubmit (사용자가 프롬프트 제출할 때마다)
# 입력: stdin으로 JSON 수신
# 동작:
#   - 현재 브랜치가 feat/new-promt-* 이면 아무것도 하지 않음 (빠른 exit)
#   - 그 외 브랜치면 feat/pr-develop 으로 이동 후 새 세션 브랜치 생성
#   - 이유: 세션 중에 pr-develop에 머지 → 세션 브랜치 삭제된 뒤 다음 프롬프트가 와도
#     Claude가 실수로 pr-develop에서 직접 작업하지 못하게 강제.
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

INPUT=$(cat 2>/dev/null || true)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
cd "${CWD:-$(git rev-parse --show-toplevel 2>/dev/null)}" 2>/dev/null || exit 0

CURRENT=$(git branch --show-current 2>/dev/null || echo "")

# 이미 세션 브랜치 → 아무것도 하지 않음
case "$CURRENT" in
  feat/new-promt-*) exit 0 ;;
esac

# feat/pr-develop 준비 (없으면 develop 기준으로 생성)
if ! git rev-parse --verify feat/pr-develop >/dev/null 2>&1; then
  if git rev-parse --verify develop >/dev/null 2>&1; then
    git checkout develop >/dev/null 2>&1 || exit 0
    git checkout -b feat/pr-develop >/dev/null 2>&1 || exit 0
  else
    # develop 자체가 없으면 조용히 포기 (SessionStart가 이미 경고했을 것)
    exit 0
  fi
fi

# 세션 브랜치로 전환
git checkout feat/pr-develop >/dev/null 2>&1 || exit 0
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
SESSION_BRANCH="feat/new-promt-${TIMESTAMP}"

if git checkout -b "$SESSION_BRANCH" >/dev/null 2>&1; then
  jq -n --arg branch "$SESSION_BRANCH" --arg from "$CURRENT" '{
    "systemMessage": ("세션 브랜치 재생성: " + $branch + " (이전 위치: " + $from + ")"),
    "hookSpecificOutput": {
      "hookEventName": "UserPromptSubmit",
      "additionalContext": ("현재 세션 브랜치: " + $branch + ". 이 브랜치에서만 작업하세요. feat/pr-develop에서 직접 작업하지 마세요.")
    }
  }'
fi

exit 0
