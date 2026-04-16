#!/usr/bin/env bash
# 세션 시작 시 브랜치 자동 생성
# develop → feat/pr-develop → feat/session-YYYYMMDD-HHMMSS
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

msg() { printf '{"systemMessage":"%s"}\n' "$1"; }

CURRENT=$(git branch --show-current 2>/dev/null)
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
SESSION_BRANCH="feat/session-${TIMESTAMP}"

# feat/pr-develop 브랜치가 없으면 develop에서 생성
if ! git rev-parse --verify feat/pr-develop >/dev/null 2>&1; then
  if git rev-parse --verify develop >/dev/null 2>&1; then
    git checkout develop 2>/dev/null
    git checkout -b feat/pr-develop 2>/dev/null
    msg "feat/pr-develop 브랜치 생성 (from develop)"
  else
    msg "⚠️ develop 브랜치가 없습니다. 먼저 develop 브랜치를 생성하세요."
    exit 0
  fi
else
  git checkout feat/pr-develop 2>/dev/null
fi

# 세션 브랜치 생성
git checkout -b "$SESSION_BRANCH" 2>/dev/null

msg "세션 브랜치 생성: ${SESSION_BRANCH} (from feat/pr-develop)"
exit 0
