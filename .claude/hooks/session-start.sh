#!/usr/bin/env bash
# ============================================================================
# SessionStart Hook — 통합 브랜치(feat/pr-develop) 준비만 담당
# 트리거: SessionStart (matcher: "startup")
# 입력: stdin으로 JSON 수신 (session_id, cwd, source 등)
# 출력: JSON systemMessage + additionalContext
#
# 정책 (2026-04-20 갱신 — "지연 생성"으로 전환):
#   · 세션 브랜치(feat/new-prompt-*)는 **이 훅에서 만들지 않음**
#   · 실제 Edit/Write가 필요한 시점에 PreToolUse(check-branch.sh)가 생성
#   · Stop(auto-commit.sh)에서도 pr-develop에 변경이 남아있으면 커밋 직전 자동 분기
# 따라서 이 훅은 "통합 브랜치 존재 + 체크아웃"만 보장한다.
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
cd "${CWD:-$(git rev-parse --show-toplevel 2>/dev/null)}" || exit 0

# feat/pr-develop 브랜치가 없으면 develop에서 생성
if ! git rev-parse --verify feat/pr-develop >/dev/null 2>&1; then
  if git rev-parse --verify develop >/dev/null 2>&1; then
    git checkout develop >/dev/null 2>&1
    git checkout -b feat/pr-develop >/dev/null 2>&1
    jq -n '{
      "systemMessage": "feat/pr-develop 브랜치 생성 완료 (from develop). 세션 브랜치는 실제 Edit/Write 시 자동 생성됩니다.",
      "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "현재 브랜치: feat/pr-develop. 세션 브랜치(feat/new-prompt-*)는 Edit/Write가 필요한 순간 PreToolUse 훅이 자동 생성합니다. 브랜치 생성·체크는 수동으로 하지 마세요."
      }
    }'
    exit 0
  else
    echo "develop 브랜치가 없습니다. 먼저 develop 브랜치를 생성하세요." >&2
    exit 2
  fi
fi

# pr-develop으로 이동만 (세션 브랜치 생성 없음)
git checkout feat/pr-develop >/dev/null 2>&1

jq -n '{
  "systemMessage": "통합 브랜치 feat/pr-develop으로 이동 완료. 세션 브랜치는 Edit/Write 시 자동 생성됩니다.",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "현재 브랜치: feat/pr-develop. 세션 브랜치(feat/new-prompt-*)는 Edit/Write가 필요한 순간 PreToolUse 훅이 자동 생성합니다. 브랜치 생성·체크를 수동으로 하지 마세요."
  }
}'

exit 0
