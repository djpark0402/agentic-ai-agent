#!/usr/bin/env bash
# ============================================================================
# PostToolUse Hook — 파일 저장 직후 lint 검사
# 트리거: PostToolUse (matcher: "Write|Edit")
# 입력: stdin으로 JSON 수신 (tool_name, tool_input.file_path 등)
# 출력: JSON additionalContext (lint 결과를 Claude에 전달)
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

# stdin에서 이벤트 데이터 읽기
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# 파일 경로가 없으면 종료
if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# 파일 확장자별 lint 실행
case "$FILE_PATH" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      if ! ruff check "$FILE_PATH" >/tmp/claude-post-lint.log 2>&1; then
        ERRORS=$(cat /tmp/claude-post-lint.log)
        jq -n --arg errors "$ERRORS" --arg file "$FILE_PATH" '{
          "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ("⚠️ " + $file + " ruff lint 경고:\n" + $errors)
          }
        }'
        exit 0
      fi
    fi
    ;;
  *.ts|*.tsx)
    if [ -f "frontend/node_modules/.bin/eslint" ]; then
      if ! frontend/node_modules/.bin/eslint "$FILE_PATH" >/tmp/claude-post-lint.log 2>&1; then
        ERRORS=$(cat /tmp/claude-post-lint.log)
        jq -n --arg errors "$ERRORS" --arg file "$FILE_PATH" '{
          "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ("⚠️ " + $file + " eslint 경고:\n" + $errors)
          }
        }'
        exit 0
      fi
    fi
    ;;
esac

exit 0
