#!/usr/bin/env bash
# ============================================================================
# SessionStart Hook — develop · pr-develop · 세션 브랜치까지 모두 보장
# 트리거: SessionStart (matcher: "startup")
# 입력: stdin으로 JSON 수신 (session_id, cwd, source 등)
# 출력: JSON systemMessage + additionalContext
#
# 정책:
#   1) develop이 없으면 main → master 순서로 기준을 찾아 develop 자동 생성
#   2) feat/pr-develop이 없으면 develop에서 생성
#   3) feat/new-prompt-*가 없으면 pr-develop에서 새 세션 브랜치 즉시 생성
#      — 있으면 그 브랜치로 체크아웃해 이어서 작업 (항상 1개만 유지)
#
# 작업이 끝나면 Stop 훅(auto-commit.sh)이 머지 질문을 강제하며,
# 사용자가 승인하면 pr-develop에 --no-ff로 1회 머지 후 세션 브랜치를 삭제한다.
# 머지 거부 시 세션 브랜치는 유지되어 다음 세션에서 이어 작업한다.
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

# 세션 내내 주입할 워크플로 규칙 (모든 additionalContext 공통)
WORKFLOW_RULE="[브랜치 워크플로 규칙]
- 현재 세션 브랜치(feat/new-prompt-*)에서만 작업할 것
- 작업 완료 시 반드시 사용자에게 'feat/pr-develop에 머지할까요?' 질문 (Stop 훅 block 강제)
- 머지되면 세션 브랜치 삭제, 머지 거부되면 유지
- 머지 완료 후 반드시 'develop으로 PR 생성할까요?' 질문 (PostToolUse check-merge.sh block 강제)
- 위 질문을 절대 생략·요약·병합하지 말 것"

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
cd "${CWD:-$(git rev-parse --show-toplevel 2>/dev/null)}" || exit 0

CREATED=""

# ── 1단계: develop 확보 (없으면 main/master에서 생성) ─────────────────────────
if ! git rev-parse --verify develop >/dev/null 2>&1; then
  if git rev-parse --verify main >/dev/null 2>&1; then
    DEV_SRC="main"
  elif git rev-parse --verify master >/dev/null 2>&1; then
    DEV_SRC="master"
  else
    echo "develop/main/master 중 어느 브랜치도 없습니다. 최소 하나의 기준 브랜치를 먼저 만들어 주세요." >&2
    exit 2
  fi
  git checkout "$DEV_SRC" >/dev/null 2>&1
  git checkout -b develop >/dev/null 2>&1
  CREATED="${CREATED}develop(from ${DEV_SRC}) "
fi

# ── 2단계: feat/pr-develop 확보 ─────────────────────────────────────────────
if ! git rev-parse --verify feat/pr-develop >/dev/null 2>&1; then
  git checkout develop >/dev/null 2>&1
  git checkout -b feat/pr-develop >/dev/null 2>&1
  CREATED="${CREATED}feat/pr-develop "
fi

# pr-develop으로 이동 (세션 브랜치 체크아웃을 위한 기준점)
git checkout feat/pr-develop >/dev/null 2>&1

# ── 3단계: 세션 브랜치 확보 (없으면 즉시 생성, 있으면 이어서 작업) ────────────
EXISTING_SESSION=$(git for-each-ref --sort=-committerdate \
  --format='%(refname:short)' \
  'refs/heads/feat/new-prompt-*' 2>/dev/null | head -1)

if [ -n "$EXISTING_SESSION" ]; then
  git checkout "$EXISTING_SESSION" >/dev/null 2>&1
  SESSION_BRANCH="$EXISTING_SESSION"
  ACTION="기존 세션 브랜치 ${SESSION_BRANCH}를 이어서 사용합니다."
else
  SESSION_BRANCH="feat/new-prompt-$(date +%Y%m%d-%H%M%S)"
  git checkout -b "$SESSION_BRANCH" >/dev/null 2>&1
  CREATED="${CREATED}${SESSION_BRANCH} "
  ACTION="세션 브랜치 ${SESSION_BRANCH}를 새로 만들었습니다."
fi

if [ -n "$CREATED" ]; then
  MSG="[SessionStart] 자동 생성: ${CREATED}| ${ACTION}"
else
  MSG="[SessionStart] ${ACTION}"
fi

jq -n --arg b "$SESSION_BRANCH" --arg msg "$MSG" --arg rule "$WORKFLOW_RULE" '{
  "systemMessage": $msg,
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ("현재 브랜치: " + $b + ". 이 세션 브랜치 하나로만 작업합니다. pr-develop에 머지되면 삭제되고, 머지 거부되면 유지되어 다음 세션에서 이어집니다.\n\n" + $rule)
  }
}'

exit 0
