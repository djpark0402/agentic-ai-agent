import json

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .llm import stream_events
from .models import Conversation, Message
from .routes.conversations import router as conversations_router
from .routes.settings import get_base_url, router as settings_router
from .schemas import ChatRequest
from .tools import TOOL_SCHEMAS, call_tool

MAX_TOOL_ITERATIONS = 3

# 최근 N턴만 LLM에 전달하는 슬라이딩 윈도우 크기 (user/assistant 메시지 합계 기준)
HISTORY_WINDOW = 20

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # vite dev 서버
        "http://localhost:54084",  # docker 프론트엔드 노출 포트
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations_router)
app.include_router(settings_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(req: ChatRequest, session: AsyncSession = Depends(get_session)):
    last_user_preview = ""
    if req.messages:
        last = req.messages[-1]
        last_user_preview = f"[{last.role}] {last.content[:200]}"
    print("#" * 80)
    print(
        f"[CHAT REQUEST] conversation_id={req.conversation_id} model={req.model} "
        f"frontend_messages={len(req.messages)}턴 system={(req.system or '')[:80]}"
    )
    print(f"[CHAT REQUEST] 마지막 메시지: {last_user_preview}")

    # 대화 저장: conversation_id가 있으면 user 메시지를 DB에 기록하고
    # DB의 기존 이력(최근 HISTORY_WINDOW턴) + 새 user 메시지를 LLM에 전달
    conv: Conversation | None = None
    messages_for_llm = req.messages
    if req.conversation_id is not None:
        conv = await session.get(Conversation, req.conversation_id)
        if conv is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="conversation not found")

        last_user = req.messages[-1] if req.messages else None
        if last_user is not None and last_user.role == "user":
            session.add(
                Message(
                    conversation_id=conv.id,
                    role="user",
                    content=last_user.content,
                )
            )
            await session.commit()

        # DB에서 최근 HISTORY_WINDOW개의 메시지를 가져와 LLM 입력 구성
        from sqlmodel import select

        stmt = (
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(HISTORY_WINDOW)
        )
        result = await session.execute(stmt)
        recent = list(reversed(result.scalars().all()))
        from .schemas import Message as MessageSchema

        messages_for_llm = [
            MessageSchema(role=m.role, content=m.content) for m in recent
        ]
        print(
            f"[CHAT CONTEXT] DB에서 최근 {len(messages_for_llm)}턴 로드 "
            f"(conv={conv.id}, sliding window={HISTORY_WINDOW})"
        )
        for i, m in enumerate(messages_for_llm):
            print(f"  [{i}] ({m.role}) {m.content[:200]}")

    # 로컬 function-calling 도구 — 마지막 user 메시지에 트리거 키워드가 포함될 때만
    # tools를 주입해 일반 대화가 업스트림 호환성을 해치지 않게 한다.
    tools_schema: list[dict] | None = None
    last_text = req.messages[-1].content if req.messages else ""
    if any(k in last_text for k in ("코스피", "코스닥", "KOSPI", "KOSDAQ", "주식", "시가총액", "주가")):
        tools_schema = TOOL_SCHEMAS
        print(f"[CHAT TOOLS] 트리거 감지 → tools={len(tools_schema)}건 주입")

    # stream_events에 넘길 messages를 OpenAI-dict 형식으로 변환 (tool 루프에서 어차피 필요)
    llm_messages: list[dict] = [
        {"role": m.role, "content": m.content} for m in messages_for_llm
    ]

    # BASE_URL: DB에 저장된 설정이 있으면 우선 사용, 없으면 env 폴백
    base_url_value, base_url_source = await get_base_url(session)
    print(f"[CHAT BASE_URL] {base_url_value} (source={base_url_source})")

    async def event_stream():
        full_reply = ""
        try:
            for iteration in range(MAX_TOOL_ITERATIONS + 1):
                tool_calls_to_run: list[dict] | None = None
                iter_reply = ""
                async for ev in stream_events(
                    llm_messages, req.system, req.model, tools=tools_schema,
                    base_url=base_url_value,
                ):
                    t = ev.get("type")
                    if t == "tool_calls":
                        tool_calls_to_run = ev.get("tool_calls") or []
                        continue
                    if t == "token":
                        iter_reply += ev.get("content", "")
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

                if not tool_calls_to_run:
                    full_reply += iter_reply
                    break

                if iteration == MAX_TOOL_ITERATIONS:
                    msg = f"도구 호출 최대 반복({MAX_TOOL_ITERATIONS}) 초과 — 중단"
                    yield f"data: {json.dumps({'type': 'error', 'message': msg}, ensure_ascii=False)}\n\n"
                    return

                # assistant(tool_calls) 메시지를 대화에 추가 후 각 도구 실행 → tool 메시지 append
                llm_messages.append(
                    {"role": "assistant", "content": None, "tool_calls": tool_calls_to_run}
                )
                for tc in tool_calls_to_run:
                    tname = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"] or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    yield (
                        "data: "
                        + json.dumps(
                            {"type": "status", "stage": "tool_start",
                             "label": f"도구 호출: {tname}({args})", "tool": tname},
                            ensure_ascii=False,
                        )
                        + "\n\n"
                    )
                    print(f"[TOOL CALL] {tname} args={args}")
                    try:
                        tool_result = await call_tool(tname, args)
                    except Exception as tool_err:
                        tool_result = json.dumps({"error": str(tool_err)}, ensure_ascii=False)
                    print(f"[TOOL RESULT] {tname} → {tool_result[:500]}")
                    llm_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result,
                        }
                    )
                    yield (
                        "data: "
                        + json.dumps(
                            {"type": "status", "stage": "tool_end",
                             "label": f"도구 완료: {tname}", "tool": tname},
                            ensure_ascii=False,
                        )
                        + "\n\n"
                    )
                # 루프 재진입 — 이번엔 LLM이 최종 응답을 스트리밍할 것
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            return

        if conv is not None and full_reply:
            session.add(
                Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=full_reply,
                )
            )
            await session.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
