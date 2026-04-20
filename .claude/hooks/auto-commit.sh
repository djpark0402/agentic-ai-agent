#!/usr/bin/env bash
# ============================================================================
# Stop Hook — lint 검사 + 자동 커밋 + 머지 알림
# 트리거: Stop (매 프롬프트 턴 종료 시)
# 입력: stdin으로 JSON 수신 (session_id, cwd, last_assistant_message 등)
# 출력: JSON systemMessage (커밋 결과 + 머지 알림)
# 참고: https://code.claude.com/docs/ko/hooks
# ============================================================================
set -u

# stdin에서 이벤트 데이터 읽기
INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

cd "${CWD:-$(git rev-parse --show-toplevel 2>/dev/null)}" || exit 0

BRANCH=$(git branch --show-current 2>/dev/null)

# ── 변경사항 확인 ──
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo '{"systemMessage":"변경사항 없음 — 자동 커밋 건너뜀"}'
  exit 0
fi

# ── Python lint ──
PY_FILES=$({ git diff --name-only HEAD -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u)

if [ -n "$PY_FILES" ]; then
  if command -v ruff >/dev/null 2>&1; then
    if ! echo "$PY_FILES" | xargs ruff check >/tmp/claude-lint.log 2>&1; then
      echo '{"systemMessage":"⚠️ ruff lint 실패 — 자동 커밋 중단 (/tmp/claude-lint.log 확인)"}'
      exit 0
    fi
  elif command -v flake8 >/dev/null 2>&1; then
    if ! echo "$PY_FILES" | xargs flake8 >/tmp/claude-lint.log 2>&1; then
      echo '{"systemMessage":"⚠️ flake8 lint 실패 — 자동 커밋 중단"}'
      exit 0
    fi
  else
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      if ! python3 -m py_compile "$f" 2>/dev/null; then
        jq -n --arg file "$f" '{
          "systemMessage": ("⚠️ python 구문 오류 (" + $file + ") — 자동 커밋 중단")
        }'
        exit 0
      fi
    done <<< "$PY_FILES"
  fi
fi

# ── Frontend lint (TypeScript) ──
TS_FILES=$({ git diff --name-only HEAD -- 'frontend/*.ts' 'frontend/*.tsx'; git ls-files --others --exclude-standard -- 'frontend/*.ts' 'frontend/*.tsx'; } | sort -u)

if [ -n "$TS_FILES" ]; then
  if [ -f "frontend/node_modules/.bin/eslint" ]; then
    if ! echo "$TS_FILES" | xargs frontend/node_modules/.bin/eslint >/tmp/claude-frontend-lint.log 2>&1; then
      echo '{"systemMessage":"⚠️ eslint lint 실패 — 자동 커밋 중단 (/tmp/claude-frontend-lint.log 확인)"}'
      exit 0
    fi
  elif [ -f "frontend/tsconfig.json" ]; then
    if ! (cd frontend && npx tsc --noEmit >/tmp/claude-frontend-lint.log 2>&1); then
      echo '{"systemMessage":"⚠️ tsc 타입 체크 실패 — 자동 커밋 중단 (/tmp/claude-frontend-lint.log 확인)"}'
      exit 0
    fi
  fi
fi

# ── 스테이징 (.env 보호) ──
git add -A
git reset -- '**/.env' '.env' 2>/dev/null || true

if git diff --cached --quiet; then
  echo '{"systemMessage":"스테이징할 변경사항 없음"}'
  exit 0
fi

# ── 커밋 메시지 생성: 카테고리 감지 + 파일 목록 요약 ──
STAGED=$(git diff --cached --name-only | sort -u)
COUNT=$(echo "$STAGED" | grep -c . || true)

# 최상위 경로로 카테고리 감지 (순서 유지: backend, frontend, docs, hooks, ci, project)
CATS=""
echo "$STAGED" | grep -q '^backend/' && CATS="${CATS}+backend"
echo "$STAGED" | grep -q '^frontend/' && CATS="${CATS}+frontend"
echo "$STAGED" | grep -q '^docs/' && CATS="${CATS}+docs"
echo "$STAGED" | grep -q '^\.claude/' && CATS="${CATS}+hooks"
echo "$STAGED" | grep -q '^\.github/' && CATS="${CATS}+ci"
# 루트/기타 파일이 있으면 project 추가 (CLAUDE.md, docker-compose.yml 등)
if echo "$STAGED" | grep -qv '^\(backend/\|frontend/\|docs/\|\.claude/\|\.github/\)'; then
  CATS="${CATS}+project"
fi
CATS=${CATS#+}          # 앞 '+' 제거
[ -z "$CATS" ] && CATS="misc"

# 파일 요약: basename 기준으로 앞 3개 + 나머지 개수
FIRST_BASENAMES=$(echo "$STAGED" | head -3 | awk -F/ '{print $NF}' | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
if [ "$COUNT" -gt 3 ]; then
  FILE_SUMMARY="${FIRST_BASENAMES} 외 $((COUNT-3))건"
else
  FILE_SUMMARY="${FIRST_BASENAMES}"
fi

COMMIT_TITLE="chore(${CATS}): ${FILE_SUMMARY}"

COMMIT_MSG="${COMMIT_TITLE}

Co-Authored-By: Claude <noreply@anthropic.com>"

if git commit -m "$COMMIT_MSG" >/tmp/claude-auto-commit.log 2>&1; then
  SHA=$(git rev-parse --short HEAD)

  # 세션 브랜치(feat/new-promt-*)에서 작업 중이면 block으로 Claude를 다시 깨워 머지 질문을 강제
  if echo "$BRANCH" | grep -q '^feat/new-promt-'; then
    jq -n --arg branch "$BRANCH" --arg sha "$SHA" '{
      "decision": "block",
      "reason": ("✅ 세션 브랜치(" + $branch + ")에 로컬 자동 커밋 완료 (" + $sha + "). 사용자에��� 반드시 feat/pr-develop에 머지할까요? 라고 물어보세요.")
    }'
  else
    jq -n --arg branch "$BRANCH" --arg sha "$SHA" '{
      "systemMessage": ("✅ " + $branch + " 브랜치에 로컬 자동 커밋 완료 (" + $sha + ")")
    }'
  fi
else
  echo '{"systemMessage":"❌ 자동 커밋 실패 — /tmp/claude-auto-commit.log 확인"}'
fi

exit 0
