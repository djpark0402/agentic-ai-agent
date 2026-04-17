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

## 6. Hook 수명주기 1:1 매핑표

> [공식 문서](https://code.claude.com/docs/ko/hooks)의 Hook 수명주기 전체 이벤트와
> 본 프로젝트의 사용 여부를 1:1 매핑한 표입니다.

### 6-1. 세션 수명주기 (Session Lifecycle)

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **SessionStart** | 세션 시작/재개 | ✅ 사용 | `session-start.sh` — feat/pr-develop → feat/new-promt-* 브랜치 자동 생성 |
| **InstructionsLoaded** | CLAUDE.md/rules 로드 | ❌ 미사용 | CLAUDE.md가 기본 로딩되므로 별도 훅 불필요 |
| **SessionEnd** | 세션 종료 | ❌ 미사용 | 종료 시 특별한 처리 없음 (자동 커밋은 Stop에서 처리) |

### 6-2. 사용자 입력 (User Input)

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **UserPromptSubmit** | 프롬프트 제출 시 (Claude 처리 전) | ❌ 미사용 | 프롬프트 검증/필터링 필요 없음. 향후 금지어 필터 등에 활용 가능 |

### 6-3. 도구 수명주기 (Tool Lifecycle) — 에이전트 루프 내 반복

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **PreToolUse** | 도구 실행 전 (차단 가능) | ✅ 사용 | `settings.json` 인라인 — Edit/Write(**/.env) 차단 (`exit 2`) |
| **PermissionRequest** | 권한 대화 상자 표시 | ❌ 미사용 | permissions deny/ask 규칙으로 충분. 향후 자동 승인 정책에 활용 가능 |
| **PostToolUse** | 도구 실행 성공 후 | ✅ 사용 | `post-lint.sh` — Write/Edit 후 즉시 lint 검사 (ruff/eslint) |
| **PostToolUseFailure** | 도구 실행 실패 후 | ❌ 미사용 | 실패 시 별도 처리 없음. 향후 에러 로깅에 활용 가능 |
| **PermissionDenied** | 자동 모드에서 거부 | ❌ 미사용 | auto 모드 미사용 (default 모드 운영) |

### 6-4. 에이전트 및 작업 (Agent & Task)

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **SubagentStart** | Subagent 생성 시 | ❌ 미사용 | 서브에이전트 생성 시 별도 처리 없음 |
| **SubagentStop** | Subagent 완료 시 | ❌ 미사용 | 서브에이전트 종료 시 별도 처리 없음 |
| **TaskCreated** | 작업 생성 시 | ❌ 미사용 | 작업 관리 훅 미적용 |
| **TaskCompleted** | 작업 완료 시 | ❌ 미사용 | 작업 관리 훅 미적용 |
| **TeammateIdle** | 팀원 유휴 전환 시 | ❌ 미사용 | 팀 모드 미사용 |

### 6-5. 제어 흐름 (Control Flow)

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **Stop** | Claude 응답 완료 (턴 종료) | ✅ 사용 | `auto-commit.sh` — lint → 자동 커밋 → `decision: block`으로 머지 질문 강제 |
| **StopFailure** | API 오류로 턴 종료 | ❌ 미사용 | API 오류 시 별도 처리 없음. 향후 재시도 로직에 활용 가능 |

### 6-6. 구성 및 파일 (Configuration & Files) — 비동기

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **ConfigChange** | settings 파일 변경 시 | ❌ 미사용 | 설정 변경 감지 불필요. 향후 감사 로그에 활용 가능 |
| **CwdChanged** | 작업 디렉토리 변경 시 | ❌ 미사용 | 단일 프로젝트 디렉토리에서 작업 |
| **FileChanged** | 감시 파일 변경 시 | ❌ 미사용 | 파일 감시 불필요. 향후 .env 변경 감지에 활용 가능 |

### 6-7. 컨텍스트 압축 (Compaction) — 비동기

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **PreCompact** | 압축 시작 전 | ❌ 미사용 | 압축 전 처리 불필요 |
| **PostCompact** | 압축 완료 후 | ✅ 사용 | `post-compact.sh` — 핵심 규칙 재주입 (브랜치, 머지, PR, TDD, 한글 커밋) |

### 6-8. 알림 (Notifications) — 비동기

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **Notification** | Claude Code 알림 발송 시 | ❌ 미사용 | 알림 커스터마이징 불필요. 향후 Slack 연동 등에 활용 가능 |

### 6-9. MCP (Model Context Protocol)

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **Elicitation** | MCP 서버 입력 요청 시 | ❌ 미사용 | MCP 서버 미사용 |
| **ElicitationResult** | MCP 응답 완료 후 | ❌ 미사용 | MCP 서버 미사용 |

### 6-10. 버전 제어 (Version Control)

| 공식 이벤트 | 발생 시점 | 사용 여부 | 본 프로젝트 적용 내용 |
|:----------:|----------|:--------:|-------------------|
| **WorktreeCreate** | Git worktree 생성 시 | ❌ 미사용 | worktree 미사용 (세션 브랜치로 대체) |
| **WorktreeRemove** | Worktree 제거 시 | ❌ 미사용 | worktree 미사용 |

---

### 6-11. 사용 현황 요약

```
공식 Hook 이벤트: 총 23개
├── ✅ 사용 중: 5개 (22%)
│   ├── SessionStart  → session-start.sh (브랜치 자동 생성)
│   ├── PreToolUse    → 인라인 command (.env 차단)
│   ├── PostToolUse   → post-lint.sh (즉시 lint)
│   ├── PostCompact   → post-compact.sh (압축 후 핵심 규칙 재주입)
│   └── Stop          → auto-commit.sh (자동 커밋 + block 머지 알림)
│
└── ❌ 미사용: 18개 (78%)
    ├── 현재 불필요: 15개 (단일 프로젝트, MCP 미사용 등)
    └── 향후 활용 가능: 3개
        ├── UserPromptSubmit — 금지어 필터
        ├── Notification — Slack 연동
        └── FileChanged — .env 변경 감지
```

### 6-12. 수명주기 흐름도 (본 프로젝트 적용)

> 미사용 이벤트는 <span style="color:red">빨간색</span>으로 표시됩니다.

<table>
<tr><td colspan="2" align="center"><b>Claude Code 실행</b></td></tr>
<tr><td colspan="2" align="center">▼</td></tr>

<tr><td colspan="2">
<table width="100%" style="border:2px solid #333;">
<tr><td><b>① SessionStart</b> ✅<br/>
&nbsp;&nbsp;session-start.sh 실행<br/>
&nbsp;&nbsp;→ develop → feat/pr-develop → feat/new-promt-*
</td></tr>
</table>
</td></tr>

<tr><td colspan="2">
&nbsp;&nbsp;<span style="color:red">InstructionsLoaded (미사용)</span> <span style="color:gray">— 압축 후 커스텀 규칙 재주입, 디렉토리별 규칙 분기</span>
</td></tr>

<tr><td colspan="2" align="center">▼</td></tr>

<tr><td colspan="2">
<table width="100%" style="border:2px solid #333;">

<tr><td><span style="color:red">UserPromptSubmit (미사용)</span> <span style="color:gray">— 금지어 필터, 프롬프트 로깅, 입력 검증</span></td></tr>
<tr><td><hr/></td></tr>

<tr><td>
<table width="95%" align="center" style="border:1px dashed #666;">
<tr><td align="center"><b>에이전트 루프 (반복)</b></td></tr>
<tr><td><br/>

<b>② PreToolUse</b> ✅<br/>
&nbsp;&nbsp;Edit/Write(**/.env) → exit 2 차단<br/>
&nbsp;&nbsp;&nbsp;&nbsp;│<br/>
<span style="color:red">&nbsp;&nbsp;PermissionRequest (미사용)</span> <span style="color:gray">— npm/yarn 자동 승인, 사내 도구 자동 허용</span><br/>
&nbsp;&nbsp;&nbsp;&nbsp;│<br/>
&nbsp;&nbsp;&nbsp;&nbsp;▼<br/>
<table width="90%" align="center" style="border:2px solid #0969da; background-color:#ddf4ff;">
<tr><td>
<b style="color:#0969da;">★ 실제 코드 작성 구간 (도구 실행)</b><br/>
&nbsp;&nbsp;Claude가 이 단계에서 파일을 생성/수정합니다.<br/><br/>
&nbsp;&nbsp;<b>Edit</b> — 기존 파일 수정 (backend/*.py, frontend/*.ts 등)<br/>
&nbsp;&nbsp;<b>Write</b> — 새 파일 생성 (테스트 코드, 설정 파일 등)<br/>
&nbsp;&nbsp;<b>Bash</b> — 명령 실행 (npm install, pytest, git 등)<br/>
&nbsp;&nbsp;<b>Read/Grep/Glob</b> — 코드 탐색 (수정 없음)<br/><br/>
&nbsp;&nbsp;<i>※ TDD 흐름: 테스트 Write → Bash(pytest 실패 확인) → Edit(실무 코드) → Bash(pytest 통과)</i><br/>
&nbsp;&nbsp;<i>※ 한 턴에 여러 도구가 호출되면 ②→★→③ 이 반복됩니다</i>
</td></tr>
</table>
&nbsp;&nbsp;&nbsp;&nbsp;│<br/>
&nbsp;&nbsp;&nbsp;&nbsp;▼<br/>
<b>③ PostToolUse</b> ✅<br/>
&nbsp;&nbsp;post-lint.sh 실행<br/>
&nbsp;&nbsp;→ *.py: ruff check<br/>
&nbsp;&nbsp;→ *.ts: eslint<br/>
&nbsp;&nbsp;&nbsp;&nbsp;│<br/>
<span style="color:red">&nbsp;&nbsp;PostToolUseFailure (미사용)</span> <span style="color:gray">— 실패 로깅, 자동 재시도 트리거</span><br/>
<span style="color:red">&nbsp;&nbsp;PermissionDenied (미사용)</span> <span style="color:gray">— auto 모드 거부 시 대체 명령 제안</span><br/>
<span style="color:red">&nbsp;&nbsp;SubagentStart / SubagentStop (미사용)</span> <span style="color:gray">— 서브에이전트 실행 로깅, 결과 검증</span><br/>
<span style="color:red">&nbsp;&nbsp;TaskCreated / TaskCompleted (미사용)</span> <span style="color:gray">— 작업 진행률 대시보드, Slack 알림</span><br/>
<span style="color:red">&nbsp;&nbsp;TeammateIdle (미사용)</span> <span style="color:gray">— 팀원 유휴 시 다음 작업 자동 할당</span><br/>
<span style="color:red">&nbsp;&nbsp;Elicitation / ElicitationResult (미사용)</span> <span style="color:gray">— MCP 서버 연동 시 자동 인증 처리</span><br/>

</td></tr>
</table>
</td></tr>

<tr><td><hr/></td></tr>

<tr><td>
<b>④ Stop</b> ✅<br/>
&nbsp;&nbsp;auto-commit.sh 실행<br/>
&nbsp;&nbsp;→ Python lint (ruff → flake8 → py_compile)<br/>
&nbsp;&nbsp;→ Frontend lint (eslint → tsc --noEmit)<br/>
&nbsp;&nbsp;→ git add -A (.env 제외)<br/>
&nbsp;&nbsp;→ git commit<br/>
&nbsp;&nbsp;→ decision: "block" → Claude 강제 재응답<br/>
&nbsp;&nbsp;→ <b>"feat/pr-develop에 머지할까요?"</b> 질문<br/>
<br/>
<span style="color:red">&nbsp;&nbsp;StopFailure (미사용)</span> <span style="color:gray">— API 오류 시 자동 재시도, 에러 리포트 생성</span>
</td></tr>

<tr><td><hr/></td></tr>

<tr><td>
<span style="color:red"><b>비동기 이벤트 (모두 미사용)</b></span><br/>
<span style="color:red">&nbsp;&nbsp;ConfigChange</span> <span style="color:gray">— 설정 변경 감사 로그, 무단 변경 차단</span><br/>
<span style="color:red">&nbsp;&nbsp;CwdChanged</span> <span style="color:gray">— 디렉토리 이동 시 환경 변수 자동 전환 (direnv)</span><br/>
<span style="color:red">&nbsp;&nbsp;FileChanged</span> <span style="color:gray">— .env 변경 감지, 설정 파일 hot-reload</span><br/>
<span style="color:red">&nbsp;&nbsp;PreCompact (미사용)</span> <span style="color:gray">— 압축 전 상태 백업</span><br/>
&nbsp;&nbsp;<b>PostCompact</b> ✅ <span style="color:gray">— post-compact.sh: 압축 후 핵심 규칙 재주입 (브랜치, 머지, PR, TDD)</span><br/>
<span style="color:red">&nbsp;&nbsp;Notification</span> <span style="color:gray">— Slack/Teams 알림 연동, 권한 요청 자동 응답</span><br/>
<span style="color:red">&nbsp;&nbsp;WorktreeCreate / WorktreeRemove</span> <span style="color:gray">— 병렬 작업 브랜치 격리, 자동 정리</span>
</td></tr>

<tr><td><hr/></td></tr>

<tr><td><span style="color:red">SessionEnd (미사용)</span> <span style="color:gray">— 세션 요약 리포트 생성, 작업 시간 기록</span></td></tr>

</table>
</td></tr>

<tr><td colspan="2" align="center">▼ (머지 승인 시 — Claude 수동 수행, 훅 아님)</td></tr>
<tr><td colspan="2" align="center">feat/pr-develop에 머지 + 세션 브랜치 삭제</td></tr>
<tr><td colspan="2" align="center">▼ (PR 승인 시)</td></tr>
<tr><td colspan="2" align="center">rebase → push → gh pr create</td></tr>
</table>

> 전체 시퀀스 다이어그램은 `docs/workflow-sequence.puml`을 참고하세요.
