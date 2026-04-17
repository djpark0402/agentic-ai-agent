---
name: 브랜치 워크플로 피드백
description: 작업 시작 시 반드시 세션 브랜치 생성, 완료 시 pr-develop 머지 여부 확인
type: feedback
---

작업 시작 시 반드시 feat/pr-develop에서 세션 브랜치(feat/session-YYYYMMDD-HHMMSS)를 생성하고 그 위에서 작업할 것. 작업 완료 시 "pr-develop에 머지할까요?"라고 반드시 물어볼 것.

**Why:** 사용자가 여러 차례 지적함. develop에 직접 커밋하거나 브랜치 없이 작업하면 히스토리가 꼬임.
**How to apply:** 매 작업(사용자 명령) 시작 시 → 세션 브랜치 생성 → 작업 → 커밋 → "pr-develop에 머지할까요?" 확인 → 승인 시 머지 + 세션 브랜치 삭제
