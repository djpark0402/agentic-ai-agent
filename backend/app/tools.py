"""로컬 function-calling 도구 모음.

LLM이 OpenAI 호환 tools 스키마로 호출할 수 있는 함수들을 등록한다.
새 도구 추가 절차:
  1) 아래에 async 함수 정의
  2) TOOL_SCHEMAS에 OpenAI JSON Schema 추가
  3) TOOL_FUNCTIONS에 name → callable 매핑 추가
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

import FinanceDataReader as fdr


# ---------------------------------------------------------------------------
# get_top_stocks — KOSPI/KOSDAQ Top N (FinanceDataReader, 오픈소스, 전일 종가)
# ---------------------------------------------------------------------------


def _fetch_top_sync(market: str, by: str, n: int) -> list[dict[str, Any]]:
    if market not in ("KOSPI", "KOSDAQ"):
        raise ValueError(f"market은 KOSPI 또는 KOSDAQ만 지원. 입력값={market}")
    if by not in ("market_cap", "volume", "change_rate"):
        raise ValueError(f"by는 market_cap|volume|change_rate만 지원. 입력값={by}")
    if not 1 <= n <= 50:
        raise ValueError(f"n은 1~50 범위만 지원. 입력값={n}")

    df = fdr.StockListing(market)
    colmap = {c.lower(): c for c in df.columns}
    col_cap = colmap.get("marcap") or colmap.get("marketcap") or colmap.get("market_cap")
    col_vol = colmap.get("volume")
    col_chg = (
        colmap.get("chagesratio")  # FinanceDataReader 원본 오타 컬럼
        or colmap.get("changesratio")
        or colmap.get("change_rate")
    )
    col_close = colmap.get("close")
    col_code = colmap.get("code") or colmap.get("symbol")
    col_name = colmap.get("name")

    sort_key = {"market_cap": col_cap, "volume": col_vol, "change_rate": col_chg}[by]
    if sort_key is None or sort_key not in df.columns:
        raise RuntimeError(f"'{by}' 컬럼을 찾지 못했습니다. 사용 가능: {list(df.columns)}")

    top = df.sort_values(sort_key, ascending=False).head(n)
    rows: list[dict[str, Any]] = []
    for i, (_, r) in enumerate(top.iterrows(), start=1):
        rows.append(
            {
                "rank": i,
                "code": str(r[col_code]) if col_code else None,
                "name": str(r[col_name]) if col_name else None,
                "close": float(r[col_close]) if col_close and r[col_close] is not None else None,
                "market_cap": float(r[col_cap]) if col_cap else None,
                "volume": float(r[col_vol]) if col_vol else None,
                "change_rate": float(r[col_chg]) if col_chg else None,
            }
        )
    return rows


async def get_top_stocks(market: str, by: str = "market_cap", n: int = 5) -> str:
    """FinanceDataReader는 블로킹 IO → executor에서 실행."""
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, _fetch_top_sync, market, by, int(n))
    return json.dumps(rows, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 등록
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_top_stocks",
            "description": (
                "한국 주식시장(KOSPI 또는 KOSDAQ)의 상위 종목 N개를 조회합니다. "
                "기준은 시가총액(market_cap), 거래량(volume), 등락률(change_rate) 중 선택. "
                "전일 종가 기준이며 무료 오픈소스(FinanceDataReader) 사용."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string",
                        "enum": ["KOSPI", "KOSDAQ"],
                        "description": "조회할 시장",
                    },
                    "by": {
                        "type": "string",
                        "enum": ["market_cap", "volume", "change_rate"],
                        "description": "정렬 기준. 기본: market_cap",
                        "default": "market_cap",
                    },
                    "n": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "description": "상위 N개. 기본: 5",
                        "default": 5,
                    },
                },
                "required": ["market"],
            },
        },
    },
]


TOOL_FUNCTIONS: dict[str, Callable[..., Awaitable[str]]] = {
    "get_top_stocks": get_top_stocks,
}


async def call_tool(name: str, arguments: dict[str, Any]) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        raise KeyError(f"등록되지 않은 도구: {name}")
    return await fn(**arguments)
