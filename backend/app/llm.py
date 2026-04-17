import os
from typing import AsyncIterator

import httpx

# from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
# from langchain_upstage import ChatUpstage

from .schemas import Message
from .signing import build_hmac_headers

DEFAULT_MODEL = os.getenv("LLM_MODEL", "solar-pro3-260323")
BASE_URL = os.getenv("BASE_URL", "http://10.47.18.100:8000/v1")
API_KEY = os.getenv("API_KEY", "")
HMAC_SECRET = os.getenv("HMAC_SECRET", "")


# def _build_lc_messages(messages: list[Message], system: str | None):
#     lc_messages = []
#     if system:
#         lc_messages.append(SystemMessage(content=system))
#     for m in messages:
#         if m.role == "user":
#             lc_messages.append(HumanMessage(content=m.content))
#         elif m.role == "assistant":
#             lc_messages.append(AIMessage(content=m.content))
#         elif m.role == "system" and not system:
#             lc_messages.append(SystemMessage(content=m.content))
#     return lc_messages


def _build_payload_messages(messages: list[Message], system: str | None) -> list[dict]:
    payload = []
    if system:
        payload.append({"role": "system", "content": system})
    for m in messages:
        payload.append({"role": m.role, "content": m.content})
    return payload


async def stream_events(
    messages: list[Message],
    system: str | None,
    model: str | None = None,
) -> AsyncIterator[dict]:
    """Yield typed events: status | token | done."""
    # --- 기존 Solar(ChatUpstage) 스트리밍 호출 (주석 처리) ---
    # llm = ChatUpstage(
    #     model=model or DEFAULT_MODEL,
    #     base_url=BASE_URL,
    #     streaming=True,
    #     temperature=0.5,
    # )
    # lc_messages = _build_lc_messages(messages, system)
    #
    # yield {"type": "status", "stage": "thinking", "label": "생각하는 중..."}
    # first_token_sent = False
    #
    # async for event in llm.astream_events(lc_messages, version="v2"):
    #     kind = event["event"]
    #
    #     if kind == "on_chat_model_stream":
    #         chunk = event["data"].get("chunk")
    #         content = getattr(chunk, "content", "") if chunk else ""
    #         if content:
    #             if not first_token_sent:
    #                 yield {"type": "status", "stage": "generating", "label": "응답 생성 중..."}
    #                 first_token_sent = True
    #             yield {"type": "token", "content": content}
    #
    #     elif kind == "on_tool_start":
    #         name = event.get("name", "tool")
    #         yield {"type": "status", "stage": "tool_start", "label": f"도구 호출: {name}", "tool": name}
    #
    #     elif kind == "on_tool_end":
    #         name = event.get("name", "tool")
    #         yield {"type": "status", "stage": "tool_end", "label": f"도구 완료: {name}", "tool": name}
    #
    # yield {"type": "done"}

    # --- HTTP POST 스트리밍 호출 (OpenAI/Solar 호환 /v1/chat/completions) ---
    import json as _json

    url = f"{BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": _build_payload_messages(messages, system),
        "stream": True,
    }

    yield {"type": "status", "stage": "thinking", "label": "생각하는 중..."}

    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if HMAC_SECRET:
        headers.update(build_hmac_headers(payload, API_KEY, HMAC_SECRET))

    print(f"[LLM REQUEST] POST {url}")
    print(_json.dumps(payload, ensure_ascii=False, indent=2))

    first_token_sent = False
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[len("data: "):]
                if data_str.strip() == "[DONE]":
                    break
                chunk = _json.loads(data_str)
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content", "")
                if content:
                    if not first_token_sent:
                        yield {"type": "status", "stage": "generating", "label": "응답 생성 중..."}
                        first_token_sent = True
                    yield {"type": "token", "content": content}

    yield {"type": "done"}

    # --- Upstage API 호출 (주석 처리, 필요 시 위 블록과 교체) ---
    # api_key = os.getenv("UPSTAGE_API_KEY", "")
    # url = f"{BASE_URL.rstrip('/')}/chat/completions"
    # headers = {
    #     "Authorization": f"Bearer {api_key}",
    #     "Content-Type": "application/json",
    # }
    # payload = {
    #     "model": model or DEFAULT_MODEL,
    #     "messages": _build_payload_messages(messages, system),
    #     "stream": False,
    # }
    #
    # yield {"type": "status", "stage": "thinking", "label": "생각하는 중..."}
    #
    # import json as _json
    # print(f"[LLM REQUEST] POST {url}")
    # print(_json.dumps(payload, ensure_ascii=False, indent=2))
    #
    # async with httpx.AsyncClient(timeout=60.0) as client:
    #     resp = await client.post(url, json=payload, headers=headers)
    #     resp.raise_for_status()
    #     data = resp.json()
    #
    # content = ""
    # choices = data.get("choices") or []
    # if choices:
    #     message = choices[0].get("message") or {}
    #     content = message.get("content", "") or ""
    #
    # if content:
    #     yield {"type": "status", "stage": "generating", "label": "응답 생성 중..."}
    #     yield {"type": "token", "content": content}
    #
    # yield {"type": "done"}
