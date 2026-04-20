#!/usr/bin/env bash
# ============================================================================
# SessionStart Hook — 세션 브랜치 자동 생성
# 트리거: SessionStart (matcher: "startup")
# 입력: stdin으로 JSON 수신 (session_id, cwd, source 등)
# 출력: JSON systemMessage 또는 additionalContext
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

# stdin에서 이벤트 데이터 읽기
INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

cd "${CWD:-$(git rev-parse --show-toplevel 2>/dev/null)}" || exit 0

TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
SESSION_BRANCH="feat/new-prompt-${TIMESTAMP}"

# feat/pr-develop 브랜치가 없으면 develop에서 생성
if ! git rev-parse --verify feat/pr-develop >/dev/null 2>&1; then
  if git rev-parse --verify develop >/dev/null 2>&1; then
    git checkout develop >/dev/null 2>&1
    git checkout -b feat/pr-develop >/dev/null 2>&1
    echo '{"systemMessage":"feat/pr-develop 브랜치 생성 완료 (from develop)"}'
  else
    echo "develop 브랜치가 없습니다. 먼저 develop 브랜치를 생성하세요." >&2
    exit 2
  fi
else
  git checkout feat/pr-develop >/dev/null 2>&1
fi

# 세션 브랜치 생성
if git checkout -b "$SESSION_BRANCH" >/dev/null 2>&1; then
  jq -n --arg branch "$SESSION_BRANCH" '{
    "systemMessage": ("세션 브랜치 생성: " + $branch + " (from feat/pr-develop)"),
    "hookSpecificOutput": {
      "hookEventName": "SessionStart",
      "additionalContext": ("현재 세션 브랜치: " + $branch + ". 이 브랜치에서만 작업하세요. feat/pr-develop에서 직접 작업하지 마세요.")
    }
  }'
else
  echo "세션 브랜치 생성 실패" >&2
  exit 2
fi

exit 0
