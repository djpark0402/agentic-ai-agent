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

# 메모리(feedback_branch_workflow.md) 규칙 — 모든 additionalContext에 공통 주입
WORKFLOW_RULE="[브랜치 워크플로 메모리 규칙]
- 작업 시작 시 반드시 feat/pr-develop이 아니라 세션 브랜치(feat/new-prompt-*)에서 작업할 것 — PreToolUse 훅이 자동으로 생성·전환
- 작업 완료 시 반드시 사용자에게 'feat/pr-develop에 머지할까요?' 라고 물어볼 것 — Stop 훅이 block 알림으로 강제
- 머지 완료 후 반드시 'develop으로 PR 생성할까요?' 라고 물어볼 것 — PostToolUse(check-merge.sh)가 block 알림으로 강제
- 위 질문들을 절대 생략·요약·병합하지 말 것"

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

  jq -n --arg msg "$MSG" --arg rule "$WORKFLOW_RULE" '{
    "systemMessage": $msg,
    "hookSpecificOutput": {
      "hookEventName": "SessionStart",
      "additionalContext": ("현재 브랜치: feat/pr-develop. 세션 브랜치(feat/new-prompt-*)는 Edit/Write가 필요한 순간 PreToolUse 훅이 자동 생성합니다. 브랜치 생성·체크는 수동으로 하지 마세요.\n\n" + $rule)
    }
  }'
  exit 0
fi

# 기존 세션 브랜치가 있으면 재사용. 정책: feat/new-prompt-* 는 항상 1개만 유지.
EXISTING_SESSION=$(git for-each-ref --sort=-committerdate \
  --format='%(refname:short)' \
  'refs/heads/feat/new-prompt-*' 2>/dev/null | head -1)

if [ -n "$EXISTING_SESSION" ]; then
  git checkout "$EXISTING_SESSION" >/dev/null 2>&1
  jq -n --arg b "$EXISTING_SESSION" --arg rule "$WORKFLOW_RULE" '{
    "systemMessage": ("기존 세션 브랜치 " + $b + " 를 이어서 사용합니다. (feat/new-prompt-*는 항상 1개 유지)"),
    "hookSpecificOutput": {
      "hookEventName": "SessionStart",
      "additionalContext": ("현재 브랜치: " + $b + ". 이 세션 브랜치 하나로만 작업하며, 새 브랜치를 만들지 않습니다. pr-develop 머지 후에만 새 세션 브랜치가 생성됩니다.\n\n" + $rule)
    }
  }'
  exit 0
fi

# 세션 브랜치가 전혀 없으면 pr-develop으로만 이동 (Edit 시 지연 생성)
git checkout feat/pr-develop >/dev/null 2>&1

jq -n --arg rule "$WORKFLOW_RULE" '{
  "systemMessage": "통합 브랜치 feat/pr-develop으로 이동 완료. 세션 브랜치는 Edit/Write 시 자동 생성됩니다.",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": ("현재 브랜치: feat/pr-develop. 세션 브랜치(feat/new-prompt-*)는 Edit/Write가 필요한 순간 PreToolUse 훅이 자동 생성합니다. 브랜치 생성·체크를 수동으로 하지 마세요.\n\n" + $rule)
  }
}'

exit 0
