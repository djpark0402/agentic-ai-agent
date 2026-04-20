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
    messages: list[Message] | list[dict],
    system: str | None,
    model: str | None = None,
    tools: list[dict] | None = None,
) -> AsyncIterator[dict]:
    """Yield typed events: status | token | tool_calls | done.

    messages는 Pydantic Message 또는 dict(OpenAI 호환) 모두 허용해 tool 루프에서
    assistant(tool_calls)/tool 메시지를 그대로 전달할 수 있게 한다.
    tools가 주어지면 요청에 포함하고, LLM이 tool_calls를 반환하면 누적해
    {"type":"tool_calls","tool_calls":[...]}을 yield한 뒤 종료(호출측이 실행 후 재호출).
    """
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

    # messages가 Pydantic이면 dict로 변환, dict이면 그대로 사용 (tool 루프용)
    if messages and isinstance(messages[0], Message):
        payload_messages = _build_payload_messages(messages, system)
    else:
        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)  # type: ignore[arg-type]

    payload: dict = {
        "model": model or DEFAULT_MODEL,
        "messages": payload_messages,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    # HMAC 서명은 실제 전송되는 raw body 바이트 기준으로 계산되어야 하므로
    # 여기서 미리 직렬화해 두고 httpx에 content=bytes로 전달한다.
    body_bytes = _json.dumps(payload, ensure_ascii=False).encode("utf-8")

    yield {"type": "status", "stage": "thinking", "label": "생각하는 중..."}

    headers = {"Content-Type": "application/json"}
    if API_KEY and HMAC_SECRET:
        headers.update(build_hmac_headers(body_bytes, API_KEY, HMAC_SECRET))
    elif API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    print("=" * 80)
    print(f"[LLM REQUEST] POST {url}")
    print("[LLM REQUEST HEADERS]")
    for k, v in headers.items():
        print(f"  {k}: {v}")
    print(f"[LLM REQUEST BODY] (messages={len(payload['messages'])}턴)")
    print(_json.dumps(payload, ensure_ascii=False, indent=2))

    first_token_sent = False
    full_reply = ""
    # tool_calls를 index별로 누적 (OpenAI 스트리밍 규격: 인자가 토큰 단위로 쪼개져 옴)
    tool_calls_acc: dict[int, dict] = {}
    finish_reason: str | None = None
    response_headers: dict[str, str] = {}
    status_code = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, content=body_bytes, headers=headers) as resp:
            status_code = resp.status_code
            response_headers = dict(resp.headers)
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
                choice0 = choices[0]
                if choice0.get("finish_reason"):
                    finish_reason = choice0["finish_reason"]
                delta = choice0.get("delta") or {}
                content = delta.get("content", "")
                if content:
                    if not first_token_sent:
                        yield {"type": "status", "stage": "generating", "label": "응답 생성 중..."}
                        first_token_sent = True
                    full_reply += content
                    yield {"type": "token", "content": content}
                # tool_calls 누적
                for tc_delta in delta.get("tool_calls") or []:
                    idx = tc_delta.get("index", 0)
                    slot = tool_calls_acc.setdefault(
                        idx, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                    )
                    if tc_delta.get("id"):
                        slot["id"] = tc_delta["id"]
                    fn = tc_delta.get("function") or {}
                    if fn.get("name"):
                        slot["function"]["name"] = fn["name"]
                    if fn.get("arguments"):
                        slot["function"]["arguments"] += fn["arguments"]

    print(f"[LLM RESPONSE] status={status_code} finish_reason={finish_reason}")
    print("[LLM RESPONSE HEADERS]")
    for k, v in response_headers.items():
        print(f"  {k}: {v}")
    print(f"[LLM RESPONSE BODY] (길이={len(full_reply)}자)")
    print(full_reply)
    if tool_calls_acc:
        print(f"[LLM RESPONSE TOOL_CALLS] {len(tool_calls_acc)}건")
        for idx, tc in sorted(tool_calls_acc.items()):
            print(f"  [{idx}] id={tc['id']} name={tc['function']['name']} args={tc['function']['arguments']}")
    print("=" * 80)

    if tool_calls_acc:
        # 호출측(main.py)이 이 리스트를 보고 MCP로 도구를 실행한 뒤 재호출
        yield {
            "type": "tool_calls",
            "tool_calls": [tool_calls_acc[i] for i in sorted(tool_calls_acc)],
        }
        return

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
