#!/usr/bin/env bash
# ============================================================================
# PreToolUse Hook — 보호 브랜치에서의 파일 수정 처리
# 트리거: PreToolUse (matcher: "Edit|Write")
#
# 정책 (2026-04-20 갱신):
#   · feat/pr-develop → 세션 브랜치를 자동 생성·전환 후 Edit 허용 (지연 생성)
#   · main / master / develop → 차단 (exit 2). 사용자가 명시적으로 느려져야 하는 곳.
#   · feat/new-prompt-* → 그대로 허용
#   · .claude/ 경로 편집은 어디서든 허용 (훅 설정 변경 등)
#
# 이 전략으로 "프롬프트 제출 시점"이 아니라 "실제 Edit/Write가 필요한 시점"
# 에만 세션 브랜치가 생성되어 빈 브랜치가 남지 않는다.
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

cd "${CWD:-$(git rev-parse --show-toplevel 2>/dev/null)}" || exit 0

BRANCH=$(git branch --show-current 2>/dev/null)

# .claude/ 설정 파일은 어디서든 수정 허용 (훅/설정 갱신 목적)
if echo "$FILE_PATH" | grep -q '\.claude/'; then
  exit 0
fi

case "$BRANCH" in
  feat/new-prompt-*)
    exit 0
    ;;
  feat/pr-develop)
    # 지연 생성: 현재 pr-develop이라면 Edit 직전에 새 세션 브랜치로 전환
    TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
    SESSION_BRANCH="feat/new-prompt-${TIMESTAMP}"
    if git checkout -b "$SESSION_BRANCH" >/dev/null 2>&1; then
      # systemMessage만 출력 (exit 0으로 tool 실행 허용)
      jq -n --arg branch "$SESSION_BRANCH" '{
        "systemMessage": ("세션 브랜치 자동 생성 및 전환: " + $branch + " (pr-develop에서 Edit 직전 지연 생성)")
      }'
      exit 0
    else
      echo "세션 브랜치 생성 실패 — 수동으로 feat/new-prompt-* 브랜치를 만들어주세요." >&2
      exit 2
    fi
    ;;
  main|master|develop)
    echo "보호 브랜치($BRANCH)에서 직접 파일을 수정할 수 없습니다. feat/pr-develop으로 이동하거나 사용자에게 브랜치 전환을 요청하세요." >&2
    exit 2
    ;;
esac

exit 0
