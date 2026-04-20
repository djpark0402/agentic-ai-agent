#!/usr/bin/env bash
# ============================================================================
# PostCompact Hook — 컨텍스트 압축 후 핵심 규칙 재주입
# 트리거: PostCompact (자동/수동 압축 완료 후)
# 입력: stdin으로 JSON 수신 (session_id, trigger, compact_summary 등)
# 출력: JSON additionalContext (Claude 컨텍스트에 규칙 재주입)
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

cd "${CWD:-$(git rev-parse --show-toplevel 2>/dev/null)}" || exit 0

BRANCH=$(git branch --show-current 2>/dev/null)

# 핵심 규칙을 additionalContext로 재주입
jq -n --arg branch "$BRANCH" '{
  "hookSpecificOutput": {
    "hookEventName": "PostCompact",
    "additionalContext": (
      "[컨텍스트 압축 후 핵심 규칙 재주입]\n\n" +

      "## 브랜치 규칙\n" +
      "- 현재 브랜치: " + $branch + "\n" +
      "- feat/pr-develop에서 직접 작업 절대 금지\n" +
      "- 반드시 feat/new-prompt-* 세션 브랜치에서만 작업할 것\n\n" +

      "## Stop 훅 머지 알림\n" +
      "- 자동 커밋 후 block 알림이 오면 반드시 사용자에게 feat/pr-develop에 머지할까요? 질문\n" +
      "- 절대 생략하지 말 것\n\n" +

      "## pr-develop 머지 후\n" +
      "- 머지 완료 후 즉시 develop으로 PR 생성할까요? 질문\n" +
      "- 절대 생략하지 말 것\n\n" +

      "## PR 생성 절차\n" +
      "- feat/pr-develop을 develop 기준으로 rebase 후 push\n" +
      "- gh pr create --base develop --head feat/pr-develop\n" +
      "- .github/PULL_REQUEST_TEMPLATE.md 템플릿 사용\n\n" +

      "## 개발 규칙\n" +
      "- TDD 우선 (red → green → refactor)\n" +
      "- 커밋 메시지는 반드시 한글로 작성\n" +
      "- .env 파일 수정 금지\n" +
      "- git push는 반드시 사용자 승인 후 진행"
    )
  }
}'

exit 0
