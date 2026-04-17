# Claude Code CI 자동화 — 다른 프로젝트 적용 가이드

> 이 문서는 agentic-ai-agent 프로젝트에서 구축한 Claude Code CI 자동화 시스템을
> 다른 프로젝트에 적용할 때의 가이드입니다.

---

## 파일 분류 총괄

```
.claude/
├── settings.json           ← 🔵 프로젝트마다 수정 필요
├── settings.local.json     ← 🔴 개인별 새로 생성 (git 미포함)
├── hooks/
│   ├── session-start.sh    ← 🟢 그대로 사용 가능
│   ├── auto-commit.sh      ← 🟡 lint 부분만 수정
│   └── post-lint.sh        ← 🟡 lint 도구에 맞게 수정
└── agents/
    ├── team.md             ← 🔵 프로젝트마다 수정 필요
    ├── backend-agent.md    ← 🔵 기술 스택에 맞게 수정
    └── frontend-agent.md   ← 🔵 기술 스택에 맞게 수정

CLAUDE.md                   ← 🔵 프로젝트마다 수정 필요
.github/
└── PULL_REQUEST_TEMPLATE.md ← 🟢 그대로 사용 가능
```

### 범례
- 🟢 **그대로 복사** — 수정 없이 사용
- 🟡 **부분 수정** — 기술 스택에 따라 lint 부분만 변경
- 🔵 **프로젝트별 수정** — 프로젝트 정보에 맞게 내용 변경
- 🔴 **개인별 생성** — git에 포함하지 않음, 각 개발자가 직접 설정

---

## 1. 🟢 그대로 복사하는 파일

### `.claude/hooks/session-start.sh`
> 세션 시작 시 `feat/pr-develop → feat/new-promt-*` 브랜치 자동 생성

프로젝트에 관계없이 동일하게 동작합니다. 브랜치 전략(develop → pr-develop → session)이
동일하다면 수정 없이 복사하세요.

**전제 조건:**
- `develop` 브랜치가 존재해야 함
- `jq` 설치 필요 (`brew install jq`)

```bash
# 복사
cp -r 원본/.claude/hooks/session-start.sh 새프로젝트/.claude/hooks/
chmod +x 새프로젝트/.claude/hooks/session-start.sh
```

### `.github/PULL_REQUEST_TEMPLATE.md`
> PR 생성 시 자동 적용되는 체크리스트 템플릿

범용적인 체크리스트(코드 품질, 테스트, 보안, 문서)이므로 그대로 사용 가능합니다.

```bash
cp -r 원본/.github/ 새프로젝트/.github/
```

---

## 2. 🟡 부분 수정하는 파일

### `.claude/hooks/auto-commit.sh`
> Stop 훅 — lint 검사 + 자동 커밋 + 머지 알림 (block)

**그대로 유지하는 부분:**
- stdin JSON 파싱 구조
- 변경사항 감지 로직
- `.env` 보호 (git reset)
- 커밋 메시지 형식
- `decision: block` 머지 알림 로직

**프로젝트에 맞게 수정하는 부분:**

| 섹션 | 현재 (Python + TypeScript) | Java 프로젝트 예시 | Go 프로젝트 예시 |
|------|--------------------------|-------------------|-----------------|
| lint 도구 | ruff → flake8 → py_compile | checkstyle → spotbugs | golangci-lint |
| 파일 패턴 | `*.py`, `frontend/*.ts` | `*.java` | `*.go` |
| lint 명령 | `ruff check`, `eslint` | `mvn checkstyle:check` | `golangci-lint run` |

**수정 예시 (Java 프로젝트):**
```bash
# ── Python lint ── 섹션을 아래로 교체
# ── Java lint ──
JAVA_FILES=$({ git diff --name-only HEAD -- '*.java'; git ls-files --others --exclude-standard -- '*.java'; } | sort -u)

if [ -n "$JAVA_FILES" ]; then
  if command -v mvn >/dev/null 2>&1; then
    if ! mvn checkstyle:check -q >/tmp/claude-lint.log 2>&1; then
      echo '{"systemMessage":"⚠️ checkstyle 실패 — 자동 커밋 중단"}'
      exit 0
    fi
  fi
fi
```

### `.claude/hooks/post-lint.sh`
> PostToolUse 훅 — 파일 저장 직후 즉시 lint

**수정 포인트:** `case` 문의 확장자와 lint 명령만 변경

```bash
# 현재
*.py)  ruff check "$FILE_PATH" ;;
*.ts)  eslint "$FILE_PATH" ;;

# Java 프로젝트로 변경
*.java)  checkstyle -c /google_checks.xml "$FILE_PATH" ;;
*.xml)   xmllint --noout "$FILE_PATH" ;;
```

---

## 3. 🔵 프로젝트별 수정하는 파일

### `.claude/settings.json`
> 공유 설정 — hooks 등록 + 공통 권한 규칙

**구조는 동일, 내용만 프로젝트에 맞게 수정:**

```json
{
  "hooks": {
    "SessionStart": [/* 그대로 복사 */],
    "Stop": [/* 그대로 복사 */],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "if": "Edit(**/.env)|Write(**/.env)",  // ← 보호할 파일 패턴 수정
          "command": "echo '보호된 파일입니다' >&2 && exit 2"
        }]
      }
    ],
    "PostToolUse": [/* lint 스크립트 경로는 동일 */]
  },
  "permissions": {
    "deny": [
      "Edit(**/.env)",       // ← 프로젝트에 맞게 보호 파일 추가
      "Write(**/.env)",
      "Edit(**/*.secret)",   // 예: 시크릿 파일 추가
      "Write(**/*.secret)"
    ],
    "ask": [
      "Bash(git push:*)",   // ← 그대로 유지
      "Bash(git push)"
    ]
  }
}
```

### `CLAUDE.md`
> Claude가 읽는 프로젝트 규칙서

**그대로 복사하는 섹션:**
- Git 워크플로
- 브랜치 전략 (develop → pr-develop → new-promt-*)
- 자동화 정책
- Claude 필수 행동 규칙

**프로젝트에 맞게 수정하는 섹션:**
- 아키텍처 설명
- 기술 스택
- 개발 워크플로 (TDD 세부사항)
- 브랜치 접두사 규칙 (필요 시)

### `.claude/agents/*.md`
> 에이전트 페르소나 정의

프로젝트의 기술 스택과 팀 구성에 맞게 전면 재작성합니다.

**예시: Java/Spring Boot 프로젝트**
```markdown
# Backend 에이전트
## 페르소나
당신은 Java/Spring Boot 백엔드 시니어 개발자입니다.
## 기술 스택
- Java 17 + Spring Boot 3.x
- JPA/Hibernate
- Gradle
## 린트: checkstyle
```

---

## 4. 🔴 개인별 생성하는 파일

### `.claude/settings.local.json`
> 개인 권한 — git에 포함하지 않음

각 개발자가 자신의 환경에 맞게 생성합니다.
프로젝트에 `.claude/settings.local.json.example` 템플릿을 제공하면 편리합니다.

```json
{
  "permissions": {
    "allow": [
      "Bash(curl *)",
      "Bash(npm *)",
      "Bash(git stash *)",
      "Bash(git checkout *)",
      "Bash(git add *)",
      "Bash(git reset *)",
      "Bash(git commit *)",
      "Bash(git branch *)",
      "Bash(git rebase *)",
      "Bash(git merge *)",
      "Bash(git pull *)",
      "Bash(git log *)",
      "Bash(git diff *)",
      "Bash(git status *)",
      "Bash(gh pr *)",
      "Read(**/.env)",
      "Skill(update-config)"
    ]
  }
}
```

---

## 5. 새 프로젝트 적용 체크리스트

```
□ 1. develop 브랜치 생성
□ 2. jq 설치 확인 (brew install jq)
□ 3. .claude/ 디렉토리 복사
     □ settings.json — 보호 파일 패턴, lint 도구 수정
     □ hooks/session-start.sh — 그대로 복사 + chmod +x
     □ hooks/auto-commit.sh — lint 섹션 수정 + chmod +x
     □ hooks/post-lint.sh — case 문 수정 + chmod +x
     □ agents/ — 기술 스택에 맞게 재작성
□ 4. CLAUDE.md 작성 — 아키텍처, 기술 스택 수정, 나머지는 복사
□ 5. .github/PULL_REQUEST_TEMPLATE.md — 그대로 복사
□ 6. .gitignore에 .claude/settings.local.json 추가
□ 7. settings.local.json.example 템플릿 생성
□ 8. Claude Code 실행하여 SessionStart 훅 동작 확인
□ 9. 파일 수정 후 Stop 훅 자동 커밋 + block 머지 알림 확인
```

---

## 6. 아키텍처 다이어그램

전체 워크플로우는 `docs/workflow-sequence.puml`을 참고하세요.

```
[사용자] → [Claude Code]
              ↓
         SessionStart 훅 → feat/new-promt-* 브랜치 생성
              ↓
         작업 수행 (TDD)
              ↓
         PreToolUse 훅 → .env 보호 검사
              ↓
         PostToolUse 훅 → 즉시 lint 검사
              ↓
         Stop 훅 → lint → 자동 커밋 → block 머지 알림
              ↓
         "pr-develop에 머지할까요?" (강제 질문)
              ↓ (승인)
         머지 + 세션 브랜치 삭제
              ↓
         "develop으로 PR 생성할까요?" (강제 질문)
              ↓ (승인)
         rebase → push → PR 생성
```
