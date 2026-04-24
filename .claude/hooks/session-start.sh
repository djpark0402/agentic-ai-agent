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
# develop이 없으면 main/master에서 develop을 먼저 만들고, 그 위에서 feat/pr-develop을 만든다.
if ! git rev-parse --verify feat/pr-develop >/dev/null 2>&1; then
  DEVELOP_SRC=""
  if ! git rev-parse --verify develop >/dev/null 2>&1; then
    if git rev-parse --verify main >/dev/null 2>&1; then
      DEVELOP_SRC="main"
    elif git rev-parse --verify master >/dev/null 2>&1; then
      DEVELOP_SRC="master"
    else
      echo "develop/main/master 중 어느 브랜치도 없습니다. 최소 하나의 기준 브랜치를 먼저 만들어 주세요." >&2
      exit 2
    fi
    git checkout "$DEVELOP_SRC" >/dev/null 2>&1
    git checkout -b develop >/dev/null 2>&1
  fi

  git checkout develop >/dev/null 2>&1
  git checkout -b feat/pr-develop >/dev/null 2>&1

  if [ -n "$DEVELOP_SRC" ]; then
    MSG="develop 브랜치를 ${DEVELOP_SRC}에서 자동 생성했고, 그 위에 feat/pr-develop을 만들었습니다. 세션 브랜치는 실제 Edit/Write 시 자동 생성됩니다."
  else
    MSG="feat/pr-develop 브랜치 생성 완료 (from develop). 세션 브랜치는 실제 Edit/Write 시 자동 생성됩니다."
  fi

  jq -n --arg msg "$MSG" '{
    "systemMessage": $msg,
    "hookSpecificOutput": {
      "hookEventName": "SessionStart",
      "additionalContext": "현재 브랜치: feat/pr-develop. 세션 브랜치(feat/new-prompt-*)는 Edit/Write가 필요한 순간 PreToolUse 훅이 자동 생성합니다. 브랜치 생성·체크는 수동으로 하지 마세요."
    }
  }'
  exit 0
fi

# 기존 세션 브랜치가 있으면 재사용. 정책: feat/new-prompt-* 는 항상 1개만 유지.
EXISTING_SESSION=$(git for-each-ref --sort=-committerdate \
  --format='%(refname:short)' \
  'refs/heads/feat/new-prompt-*' 2>/dev/null | head -1)

if [ -n "$EXISTING_SESSION" ]; then
  # 2개 이상 있으면 가장 최근 하나만 남기고 나머지는 삭제
  git for-each-ref --sort=-committerdate \
    --format='%(refname:short)' \
    'refs/heads/feat/new-prompt-*' 2>/dev/null | tail -n +2 | while read -r STALE; do
      [ -n "$STALE" ] && git branch -D "$STALE" >/dev/null 2>&1
    done

  git checkout "$EXISTING_SESSION" >/dev/null 2>&1
  jq -n --arg b "$EXISTING_SESSION" '{
    "systemMessage": ("기존 세션 브랜치 " + $b + " 를 이어서 사용합니다. (feat/new-prompt-*는 항상 1개 유지)"),
    "hookSpecificOutput": {
      "hookEventName": "SessionStart",
      "additionalContext": ("현재 브랜치: " + $b + ". 이 세션 브랜치 하나로만 작업하며, 새 브랜치를 만들지 않습니다. pr-develop 머지 후에만 새 세션 브랜치가 생성됩니다.")
    }
  }'
  exit 0
fi

# 세션 브랜치가 전혀 없으면 pr-develop으로만 이동 (Edit 시 지연 생성)
git checkout feat/pr-develop >/dev/null 2>&1

jq -n '{
  "systemMessage": "통합 브랜치 feat/pr-develop으로 이동 완료. 세션 브랜치는 Edit/Write 시 자동 생성됩니다.",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "현재 브랜치: feat/pr-develop. 세션 브랜치(feat/new-prompt-*)는 Edit/Write가 필요한 순간 PreToolUse 훅이 자동 생성합니다. 브랜치 생성·체크를 수동으로 하지 마세요."
  }
}'

exit 0
