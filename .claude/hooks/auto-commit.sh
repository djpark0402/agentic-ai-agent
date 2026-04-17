#!/usr/bin/env bash
# 세션 종료 시 python lint 후 자동 로컬 커밋
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

msg() { printf '{"systemMessage":"%s"}\n' "$1"; }

# 변경사항 없으면 종료
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  msg "변경사항 없음 — 자동 커밋 건너뜀"
  exit 0
fi

# 변경된 python 파일 수집 (tracked + untracked), 줄바꿈 구분
PY_FILES=$({ git diff --name-only HEAD -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u)

if [ -n "$PY_FILES" ]; then
  if command -v ruff >/dev/null 2>&1; then
    if ! echo "$PY_FILES" | xargs ruff check >/tmp/claude-lint.log 2>&1; then
      msg "⚠️ ruff lint 실패 — 자동 커밋 중단 (/tmp/claude-lint.log 확인)"
      exit 0
    fi
  elif command -v flake8 >/dev/null 2>&1; then
    if ! echo "$PY_FILES" | xargs flake8 >/tmp/claude-lint.log 2>&1; then
      msg "⚠️ flake8 lint 실패 — 자동 커밋 중단"
      exit 0
    fi
  else
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      if ! python3 -m py_compile "$f" 2>/dev/null; then
        msg "⚠️ python 구문 오류 ($f) — 자동 커밋 중단"
        exit 0
      fi
    done <<< "$PY_FILES"
  fi
fi

# .env 보호: 스테이징에서 제외
git add -A
git reset -- '**/.env' '.env' 2>/dev/null || true

if git diff --cached --quiet; then
  msg "스테이징할 변경사항 없음"
  exit 0
fi

COMMIT_MSG="chore: 세션 자동 커밋

Co-Authored-By: Claude <noreply@anthropic.com>"

if git commit -m "$COMMIT_MSG" >/tmp/claude-auto-commit.log 2>&1; then
  SHA=$(git rev-parse --short HEAD)
  BRANCH=$(git branch --show-current 2>/dev/null)
  msg "✅ 로컬 자동 커밋 완료 ($SHA)"

  # 세션 브랜치에서 작업 중이면 pr-develop 머지 여부를 Claude에게 알림
  if echo "$BRANCH" | grep -q '^feat/session-'; then
    msg "📌 현재 세션 브랜치($BRANCH)에서 작업 중입니다. 사용자에게 'feat/pr-develop에 머지할까요?' 라고 반드시 물어보세요."
  fi
else
  msg "❌ 자동 커밋 실패 — /tmp/claude-auto-commit.log 확인"
fi
exit 0
