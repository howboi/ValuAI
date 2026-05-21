# -*- coding: utf-8 -*-
"""
AI ??隡啣 API - ?挾鈭?FastAPI 敺垢嚗?隡啣?摩撠???REST API

???孵?嚗?  python3.12 -m uvicorn main:app --reload --port 8000

蝡舫?嚗?  GET /api/valuation?code=2330.TW
  GET /api/search?q=?啁?
  GET /api/health
"""

from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import csv
import io
import time
import traceback
import urllib.request

# ?? ?臬?挾銝?敹?蝞撘???????????????????????????
# valuation_analysis.py ?撌脣 SSL 靽桀儔嚗mport ???芸??瑁?
from valuation_analysis import (
    fetch_stock_data,
    calc_dcf,
    calc_pe_valuation,
    dynamic_weighting,
    calc_technical_levels,
)

# ?? FastAPI ?????????????????????????????????????
app = FastAPI(
    title="AI ??隡啣 API",
    description="雿輻 yfinance ??鞎∪??豢?嚗?蝞?DCF / P/E 隡啣??銵?舀?憯?",
    version="2.0.0",
)

# CORS嚗?閮勗?蝡荔?Vue / Vite嚗銝? port ?澆甇?API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ?? Response Schema (Pydantic Models) ????????????????
class ValuationResult(BaseModel):
    dcf_price:           Optional[float]
    pe_price:            Optional[float]
    weighted_fair_value: Optional[float]
    dcf_weight:          Optional[float]
    pe_weight:           Optional[float]

class MarginOfSafety(BaseModel):
    discount_10: Optional[float]
    discount_20: Optional[float]

class TechnicalLevels(BaseModel):
    resistance: dict[str, float]
    support:    dict[str, float]

class ChartCandle(BaseModel):
    time:  str
    open:  float
    high:  float
    low:   float
    close: float

class StockData(BaseModel):
    symbol:         str
    name:           Optional[str]
    sector:         Optional[str]
    current_price:  Optional[float]
    market_cap_b:   Optional[float]   # ?桐?嚗???    beta:           Optional[float]
    trailing_eps:   Optional[float]
    trailing_pe:    Optional[float]
    revenue_growth: Optional[float]
    earnings_growth:Optional[float]
    valuation:      ValuationResult
    margin_of_safety: MarginOfSafety
    technical:      TechnicalLevels
    chart_data:     list[ChartCandle]
    upside_pct:     Optional[float]   # ?詨????寧?瞏瞍脰?撟?%)
    recommendation: Optional[str]

class ApiResponse(BaseModel):
    status: str
    data:   Optional[StockData] = None
    error:  Optional[str]       = None


# ?? ?啗摮 (Mock Data) ?????????????????????????????
# ?澆?嚗?隞?Ⅳ, 銝剜??迂)
_TW_STOCKS: list[dict[str, str]] = [
    {"code": "2330.TW", "name": "台積電"},
    {"code": "2317.TW", "name": "鴻海"},
    {"code": "2454.TW", "name": "聯發科"},
    {"code": "2308.TW", "name": "台達電"},
    {"code": "2412.TW", "name": "中華電"},
    {"code": "2881.TW", "name": "富邦金"},
    {"code": "2882.TW", "name": "國泰金"},
    {"code": "2886.TW", "name": "兆豐金"},
    {"code": "2891.TW", "name": "中信金"},
    {"code": "2303.TW", "name": "聯電"},
    {"code": "3711.TW", "name": "日月光投控"},
    {"code": "2382.TW", "name": "廣達"},
    {"code": "2357.TW", "name": "華碩"},
    {"code": "2379.TW", "name": "瑞昱"},
    {"code": "3034.TW", "name": "聯詠"},
    {"code": "3008.TW", "name": "大立光"},
    {"code": "6505.TW", "name": "台塑化"},
    {"code": "1301.TW", "name": "台塑"},
    {"code": "2002.TW", "name": "中鋼"},
    {"code": "1101.TW", "name": "台泥"},
]
_STOCK_LIST_SOURCES = [
    ("TW", "https://mopsfin.twse.com.tw/opendata/t187ap03_L.csv"),
    ("TWO", "https://mopsfin.twse.com.tw/opendata/t187ap03_O.csv"),
]
_STOCK_INDEX_CACHE: list[dict[str, str]] = []
_STOCK_INDEX_EXPIRES_AT = 0.0
_STOCK_INDEX_TTL_SECONDS = 60 * 60 * 24


def _fallback_stock_index() -> list[dict[str, str]]:
    return [
        {
            "code": stock["code"].upper(),
            "bare_code": stock["code"].replace(".TW", "").replace(".TWO", "").upper(),
            "name": stock["name"],
            "full_name": stock["name"],
            "market": "TW" if stock["code"].upper().endswith(".TW") else "TWO",
        }
        for stock in _TW_STOCKS
    ]


def _fetch_market_stock_index(market: str, url: str) -> list[dict[str, str]]:
    suffix = "TW" if market == "TW" else "TWO"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        text = response.read().decode("utf-8-sig")

    rows: list[dict[str, str]] = []
    for row in csv.DictReader(io.StringIO(text)):
        bare_code = (row.get("公司代號") or "").strip()
        name = (row.get("公司簡稱") or row.get("公司名稱") or "").strip()
        full_name = (row.get("公司名稱") or name).strip()
        if not bare_code or not name:
            continue
        rows.append({
            "code": f"{bare_code}.{suffix}",
            "bare_code": bare_code.upper(),
            "name": name,
            "full_name": full_name,
            "market": market,
        })
    return rows


def get_stock_index() -> list[dict[str, str]]:
    global _STOCK_INDEX_CACHE, _STOCK_INDEX_EXPIRES_AT

    now = time.time()
    if _STOCK_INDEX_CACHE and now < _STOCK_INDEX_EXPIRES_AT:
        return _STOCK_INDEX_CACHE

    stocks: list[dict[str, str]] = []
    for market, url in _STOCK_LIST_SOURCES:
        try:
            stocks.extend(_fetch_market_stock_index(market, url))
        except Exception:
            continue

    if not stocks:
        stocks = _fallback_stock_index()

    _STOCK_INDEX_CACHE = stocks
    _STOCK_INDEX_EXPIRES_AT = now + _STOCK_INDEX_TTL_SECONDS
    return stocks


def get_stock_meta(code: str) -> Optional[dict[str, str]]:
    code_upper = code.upper()
    return next((stock for stock in get_stock_index() if stock["code"].upper() == code_upper), None)


def candidate_stock_codes(value: str) -> list[str]:
    """Accept common user input formats and return possible Yahoo tickers."""
    keyword = value.strip()
    if not keyword:
        return []

    stocks = get_stock_index()
    keyword_upper = keyword.upper()
    all_codes = {stock["code"].upper() for stock in stocks}
    by_bare_code: dict[str, list[str]] = {}
    for stock in stocks:
        by_bare_code.setdefault(stock["bare_code"].upper(), []).append(stock["code"].upper())

    if keyword_upper in all_codes:
        return [keyword_upper]

    if keyword_upper.endswith((".TW", ".TWO")):
        return [keyword_upper]

    if keyword_upper in by_bare_code:
        return by_bare_code[keyword_upper]

    for stock in stocks:
        if keyword == stock["name"] or keyword == stock["full_name"]:
            return [stock["code"].upper()]

    if keyword_upper.isdigit() and len(keyword_upper) == 4:
        return [f"{keyword_upper}.TW", f"{keyword_upper}.TWO"]

    return []


def has_stock_data(raw: dict) -> bool:
    hist = raw.get("hist")
    return bool(
        raw.get("current_price")
        or raw.get("market_cap")
        or raw.get("info")
        or (hist is not None and not hist.empty)
    )


def format_chart_data(raw: dict) -> list[ChartCandle]:
    hist = raw.get("hist")
    if hist is None or hist.empty:
        return []

    chart_data: list[ChartCandle] = []
    required_columns = ("Open", "High", "Low", "Close")
    for _, row in hist.dropna(subset=list(required_columns)).iterrows():
        timestamp = row.name
        if hasattr(timestamp, "strftime"):
            date_text = timestamp.strftime("%Y-%m-%d")
        else:
            date_text = str(timestamp)[:10]

        chart_data.append(ChartCandle(
            time=date_text,
            open=round(float(row["Open"]), 2),
            high=round(float(row["High"]), 2),
            low=round(float(row["Low"]), 2),
            close=round(float(row["Close"]), 2),
        ))

    return chart_data

# Response Schema for Search ????????????????????????
class SearchResult(BaseModel):
    code:    str
    name:    str
    display: str


# ?? ?? / ?舀摮垢暺??????????????????????????????????
@app.get("/api/search", response_model=List[SearchResult])
def search_stocks(
    q: str = Query(..., min_length=1, description="使用者輸入的關鍵字")
):
    keyword = q.strip()
    if not keyword:
        return []

    keyword_upper = keyword.upper()
    results: list[SearchResult] = []
    stocks = get_stock_index()

    if keyword_upper.endswith((".TW", ".TWO")):
        code_bare = keyword_upper.replace(".TW", "").replace(".TWO", "")
        stock = next((s for s in stocks if s["code"].upper() == keyword_upper), None)
        display_name = stock["name"] if stock else keyword_upper
        return [SearchResult(
            code=keyword_upper,
            name=display_name,
            display=f"{code_bare} {display_name}",
        )]

    seen_codes: set[str] = set()
    for s in stocks:
        code = s["code"].upper()
        if (
            keyword_upper in code
            or keyword_upper in s["bare_code"].upper()
            or keyword in s["name"]
            or keyword in s["full_name"]
        ):
            if code in seen_codes:
                continue
            seen_codes.add(code)
            market_label = "上市" if s["market"] == "TW" else "上櫃"
            results.append(SearchResult(
                code=code,
                name=s["name"],
                display=f"{s['bare_code']} {s['name']} ({market_label})",
            ))
        if len(results) >= 10:
            break

    if not results and keyword_upper.isdigit() and len(keyword_upper) == 4:
        results.extend([
            SearchResult(
                code=f"{keyword_upper}.TW",
                name=f"{keyword_upper}.TW",
                display=f"{keyword_upper} 上市 (.TW)",
            ),
            SearchResult(
                code=f"{keyword_upper}.TWO",
                name=f"{keyword_upper}.TWO",
                display=f"{keyword_upper} 上櫃 (.TWO)",
            ),
        ])

    return results

# 健康檢查 API
@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}


# ?? 銝颱摯?寧垢暺?????????????????????????????????????????
@app.get("/api/valuation", response_model=ApiResponse)
def get_valuation(
    code: str = Query(..., description="?∠巨隞?Ⅳ嚗?憒?2330.TW ??AAPL")
):
    """
    ?寞??∠巨隞?Ⅳ?瑁?摰隡啣??嚗??喟?瑽? JSON??    """
    candidates = candidate_stock_codes(code)
    if not candidates:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "僅支援台灣上市/上櫃股票查詢"},
        )

    try:
        # 1. ???豢?
        raw = None
        ticker = candidates[0]
        last_fetch_error: Exception | None = None
        for candidate in candidates:
            try:
                fetched = fetch_stock_data(candidate)
                if has_stock_data(fetched):
                    ticker = candidate
                    raw = fetched
                    break
            except Exception as e:
                last_fetch_error = e

        if raw is None:
            if last_fetch_error:
                raise last_fetch_error
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "查無此台灣上市/上櫃股票資料"},
            )

        # 2. 隡啣閮?
        dcf_result = calc_dcf(raw)
        pe_result  = calc_pe_valuation(raw)
        weighted   = dynamic_weighting(raw, dcf_result, pe_result)
        tech       = calc_technical_levels(raw)
        chart_data = format_chart_data(raw)

        # 3. ?渡??箸鞈?
        current = raw["current_price"]
        info    = raw.get("info", {})
        stock_meta = get_stock_meta(ticker)

        # 4. Calculate valuation summary.
        dcf_price  = round(dcf_result["fair_value"], 2) if dcf_result else None
        pe_price   = round(pe_result["fair_value"],  2) if pe_result  else None
        fair_value = round(weighted["fair_value"],   2) if weighted   else None
        mos_10     = round(weighted["mos_10"],        2) if weighted   else None
        mos_20     = round(weighted["mos_20"],        2) if weighted   else None
        w_dcf      = round(weighted["w_dcf"] * 100,  1) if weighted   else None
        w_pe       = round(weighted["w_pe"]  * 100,  1) if weighted   else None

        # 5. 上下檔空間與建議
        upside_pct = None
        recommendation = None
        if current and fair_value:
            upside_pct = round((fair_value - current) / current * 100, 1)
            if current <= mos_20:
                recommendation = "價格低於安全邊際，可優先研究"
            elif current <= fair_value:
                recommendation = "價格低於合理價，可分批布局"
            else:
                recommendation = "價格高於合理價，建議觀望"

        # 6. 蝯???
        return ApiResponse(
            status="success",
            data=StockData(
                symbol=ticker,
                name=(stock_meta or {}).get("name") or info.get("longName") or info.get("shortName"),
                sector=raw.get("sector"),
                current_price=round(current, 2) if current else None,
                market_cap_b=round(raw["market_cap"] / 1e9, 2) if raw.get("market_cap") else None,
                beta=round(raw["beta"], 2),
                trailing_eps=raw.get("trailing_eps"),
                trailing_pe=round(raw["trailing_pe"], 2) if raw.get("trailing_pe") else None,
                revenue_growth=round(raw["revenue_growth"] * 100, 1),
                earnings_growth=round(raw["earnings_growth"] * 100, 1),
                valuation=ValuationResult(
                    dcf_price=dcf_price,
                    pe_price=pe_price,
                    weighted_fair_value=fair_value,
                    dcf_weight=w_dcf,
                    pe_weight=w_pe,
                ),
                margin_of_safety=MarginOfSafety(
                    discount_10=mos_10,
                    discount_20=mos_20,
                ),
                technical=TechnicalLevels(
                    resistance={k: round(v, 2) for k, v in tech.get("resistance", {}).items()},
                    support={k: round(v, 2)    for k, v in tech.get("support",    {}).items()},
                ),
                chart_data=chart_data,
                upside_pct=upside_pct,
                recommendation=recommendation,
            )
        )

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] {ticker}: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=str(e))

