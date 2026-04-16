# Agentic AI Agent

React + FastAPI + LangChain(Upstage Solar) 기반 스트리밍 채팅 솔루션.

## Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # UPSTAGE_API_KEY 기입
uvicorn app.main:app --reload --port 8000
```

Upstage API 키: https://console.upstage.ai

## Frontend

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 http://localhost:5173 접속.

## 기능

- SSE 스트리밍 응답
- 멀티턴 대화 히스토리
- 시스템 프롬프트 설정
- LangChain `ChatUpstage` (solar-pro2)
