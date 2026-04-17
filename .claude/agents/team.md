# 팀 구성 — agentic-ai-agent

## 프로젝트 구조
```
/agentic-ai-agent
├── backend/    → agent-backend (Python/FastAPI/LangChain)
└── frontend/   → host-frontend (React/TypeScript/Vite)
```

## 에이전트 목록

### 1. Backend 에이전트 (`backend-agnet.md`)
- **역할**: Python/FastAPI 백엔드 시니어 개발자
- **담당**: `backend/` 디렉토리
- **기술**: Python 3.11, FastAPI, LangChain, Pydantic v2

### 2. Frontend 에이전트 (`frontend-agent.md`)
- **역할**: React/TypeScript 프론트엔드 시니어 개발자
- **담당**: `frontend/` 디렉토리
- **기술**: TypeScript, React 18, Vite 5

## 협업 규칙
- 각 에이전트는 자신의 담당 디렉토리 내 파일만 수정
- Backend ↔ Frontend 간 인터페이스 변경 시 양쪽 타입 정의를 동기화
- API 스키마 변경 시: Backend(`schemas.py`) → Frontend(`types.ts`, `api.ts`) 순서로 반영
- 공통 변경사항(CLAUDE.md, 루트 설정 파일 등)은 팀 차원에서 협의

## 공통 규칙
- TDD 우선 (red → green → refactor)
- 커밋 메시지는 한글로 작성
- `.env` 파일 수정 금지
- 모든 merge/push는 사용자 승인 필요
