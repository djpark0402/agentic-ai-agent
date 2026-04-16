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

# 변경된 python 파일 수집 (tracked + untracked)
mapfile -t PY_FILES < <({ git diff --name-only HEAD -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u)

if [ ${#PY_FILES[@]} -gt 0 ]; then
  LINT_OUTPUT=""
  if command -v ruff >/dev/null 2>&1; then
    if ! LINT_OUTPUT=$(ruff check "${PY_FILES[@]}" 2>&1); then
      msg "⚠️ ruff lint 실패 — 자동 커밋 중단. 수정 후 다시 시도."
      exit 0
    fi
  elif command -v flake8 >/dev/null 2>&1; then
    if ! LINT_OUTPUT=$(flake8 "${PY_FILES[@]}" 2>&1); then
      msg "⚠️ flake8 lint 실패 — 자동 커밋 중단."
      exit 0
    fi
  else
    for f in "${PY_FILES[@]}"; do
      if ! python3 -m py_compile "$f" 2>/dev/null; then
        msg "⚠️ python 구문 오류 ($f) — 자동 커밋 중단."
        exit 0
      fi
    done
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
  msg "✅ 로컬 자동 커밋 완료 ($SHA) — push 원하면 요청하세요"
else
  msg "❌ 자동 커밋 실패 — /tmp/claude-auto-commit.log 확인"
fi
exit 0
