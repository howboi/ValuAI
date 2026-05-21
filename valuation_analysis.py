"""
AI 金融估價分析腳本 - 階段一
功能：DCF 估價、P/E 估價、動態加權、安全邊際
用法：python valuation_analysis.py
"""

from __future__ import annotations
import os, ssl, shutil, certifi

# ──────────────────────────────────────────────────────
# Fix: curl_cffi's C layer cannot handle non-ASCII paths
# (e.g. Chinese usernames). Copy CA bundle to ASCII path.
# ──────────────────────────────────────────────────────
_CERT_SRC = certifi.where()
_CERT_DST = r"C:\certs\cacert.pem"
if not os.path.exists(_CERT_DST):
    os.makedirs(os.path.dirname(_CERT_DST), exist_ok=True)
    shutil.copy2(_CERT_SRC, _CERT_DST)

os.environ["SSL_CERT_FILE"]      = _CERT_DST
os.environ["REQUESTS_CA_BUNDLE"] = _CERT_DST
os.environ["CURL_CA_BUNDLE"]     = _CERT_DST
ssl._create_default_https_context = ssl._create_unverified_context

import yfinance as yf
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# 顏色輸出工具
# ──────────────────────────────────────────────
class Color:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    RED    = "\033[91m"
    WHITE  = "\033[97m"
    BLUE   = "\033[94m"

def header(title: str):
    print(f"\n{Color.CYAN}{Color.BOLD}{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}{Color.RESET}")

def section(title: str):
    print(f"\n{Color.YELLOW}{Color.BOLD}>> {title}{Color.RESET}")

def info(label: str, value):
    print(f"  {Color.WHITE}{label:<30}{Color.RESET}{Color.GREEN}{value}{Color.RESET}")

def warn(msg: str):
    print(f"  {Color.RED}[!] {msg}{Color.RESET}")


# ──────────────────────────────────────────────
# 1. 數據抓取模組
# ──────────────────────────────────────────────
def fetch_stock_data(ticker: str) -> dict:
    """使用 yfinance 抓取基本面與價格數據"""
    section(f"正在抓取 {ticker} 數據...")
    stock = yf.Ticker(ticker)

    info_data = stock.info or {}
    cashflow  = stock.cashflow        # DataFrame, 欄位為日期
    quarterly_cf = stock.quarterly_cashflow

    # 當前股價
    current_price = (
        info_data.get("currentPrice")
        or info_data.get("regularMarketPrice")
        or info_data.get("previousClose")
    )

    # 市值與股本
    market_cap  = info_data.get("marketCap", 0)
    shares_out  = info_data.get("sharesOutstanding", 1)

    # EPS
    trailing_eps = info_data.get("trailingEps")
    forward_eps  = info_data.get("forwardEps")

    # 本益比
    trailing_pe  = info_data.get("trailingPE")
    forward_pe   = info_data.get("forwardPE")

    # 成長率（5yr or analyst estimate）
    revenue_growth   = info_data.get("revenueGrowth", 0.05)       # 年營收成長率
    earnings_growth  = info_data.get("earningsGrowth", 0.07)      # 盈餘成長率
    earnings_q_growth= info_data.get("earningsQuarterlyGrowth", 0.05)

    # Beta & Sector
    beta   = info_data.get("beta", 1.0) or 1.0
    sector = info_data.get("sector", "Unknown")

    # 自由現金流（抓最近4季加總 or 年度FCF）
    fcf_annual = _extract_fcf(cashflow)
    fcf_quarterly = _extract_fcf(quarterly_cf, quarterly=True)

    # 過去股價（120天）
    hist = stock.history(period="6mo")

    result = {
        "ticker":          ticker,
        "current_price":   current_price,
        "market_cap":      market_cap,
        "shares_out":      shares_out,
        "trailing_eps":    trailing_eps,
        "forward_eps":     forward_eps,
        "trailing_pe":     trailing_pe,
        "forward_pe":      forward_pe,
        "revenue_growth":  revenue_growth,
        "earnings_growth": earnings_growth,
        "beta":            beta,
        "sector":          sector,
        "fcf_annual":      fcf_annual,
        "fcf_quarterly":   fcf_quarterly,
        "hist":            hist,
        "info":            info_data,
    }

    # 印出原始數據摘要
    section("原始數據摘要")
    info("股票代碼",       ticker)
    info("產業別",         sector)
    info("當前股價",       f"$ {current_price:.2f}" if current_price else "N/A")
    info("市值 (B)",       f"$ {market_cap/1e9:.2f} B" if market_cap else "N/A")
    info("Beta",           f"{beta:.2f}")
    info("Trailing EPS",   f"$ {trailing_eps:.4f}" if trailing_eps else "N/A")
    info("Forward EPS",    f"$ {forward_eps:.4f}"  if forward_eps  else "N/A")
    info("Trailing P/E",   f"{trailing_pe:.2f}"    if trailing_pe  else "N/A")
    info("Forward P/E",    f"{forward_pe:.2f}"     if forward_pe   else "N/A")
    info("年度 FCF",       f"$ {fcf_annual/1e6:.1f} M" if fcf_annual else "N/A")
    info("季度 FCF (TTM)", f"$ {fcf_quarterly/1e6:.1f} M" if fcf_quarterly else "N/A")
    info("營收成長率",     f"{revenue_growth*100:.1f}%")
    info("盈餘成長率",     f"{earnings_growth*100:.1f}%")

    return result


def _extract_fcf(cf_df: pd.DataFrame, quarterly: bool = False) -> float | None:
    """從 cashflow DataFrame 提取自由現金流"""
    if cf_df is None or cf_df.empty:
        return None
    try:
        # yfinance cashflow rows: index = 科目名稱
        idx = cf_df.index.str.lower()

        # 嘗試直接取 Free Cash Flow 行
        fcf_mask = idx.str.contains("free cash flow", na=False)
        if fcf_mask.any():
            row = cf_df[fcf_mask].iloc[0]
            if quarterly:
                return float(row.iloc[:4].sum())   # 最近4季加總
            else:
                return float(row.iloc[0])           # 最新年度

        # 備用：Operating CF - CapEx
        op_mask  = idx.str.contains("operating cash flow|total cash from operating", na=False)
        cap_mask = idx.str.contains("capital expenditure|capital expenditures", na=False)
        if op_mask.any() and cap_mask.any():
            op_row  = cf_df[op_mask].iloc[0]
            cap_row = cf_df[cap_mask].iloc[0]
            if quarterly:
                return float(op_row.iloc[:4].sum()) + float(cap_row.iloc[:4].sum())
            else:
                return float(op_row.iloc[0]) + float(cap_row.iloc[0])
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────
# 2. DCF 估價模組
# ──────────────────────────────────────────────
def calc_wacc(beta: float, market_cap: float) -> float:
    """
    WACC 估算（簡化版）
    - 無風險利率：美國10年期國債 ~4.5%
    - 市場風險溢酬：~5.5%
    - 債務成本：~4%，稅率30%，槓桿比假設30%
    """
    rf    = 0.045   # 無風險利率
    rm_rf = 0.055   # 市場風險溢酬
    ke    = rf + beta * rm_rf          # 權益成本 (CAPM)

    # 簡化：大市值（>500B）假設槓桿較低
    if market_cap > 5e11:
        wd = 0.15
    elif market_cap > 5e10:
        wd = 0.25
    else:
        wd = 0.35

    we   = 1 - wd
    kd   = 0.04 * (1 - 0.30)          # 稅後債務成本
    wacc = we * ke + wd * kd
    return max(wacc, 0.06)             # 最低6%


def calc_dcf(data: dict) -> dict | None:
    """
    DCF 估價：5年預測期 + 永續成長終值
    """
    section("DCF 估價計算")

    fcf = data["fcf_quarterly"] or data["fcf_annual"]
    if not fcf or fcf <= 0:
        warn("FCF 數據無效，跳過 DCF 估價")
        return None

    shares   = data["shares_out"]
    beta     = data["beta"]
    mktcap   = data["market_cap"]
    g_short  = min(max(data["earnings_growth"], -0.10), 0.30)  # 短期成長率，上限30%
    g_term   = 0.025                                            # 永續成長率 2.5%
    wacc     = calc_wacc(beta, mktcap)
    years    = 5

    info("基準 FCF",       f"$ {fcf/1e6:.1f} M")
    info("WACC",           f"{wacc*100:.2f}%")
    info("短期成長率 (g)", f"{g_short*100:.2f}%")
    info("永續成長率",     f"{g_term*100:.2f}%")

    # 預測現金流折現
    pv_fcfs = []
    fcf_t   = fcf
    for t in range(1, years + 1):
        # 成長率隨年數遞減，趨近永續成長率
        blend = g_short * (1 - t / (years + 1)) + g_term * (t / (years + 1))
        fcf_t = fcf_t * (1 + blend)
        pv    = fcf_t / ((1 + wacc) ** t)
        pv_fcfs.append(pv)
        print(f"    Year {t}: FCF={fcf_t/1e6:.1f}M  PV={pv/1e6:.1f}M  g={blend*100:.1f}%")

    # 終值 (Terminal Value)
    tv    = fcf_t * (1 + g_term) / (wacc - g_term)
    pv_tv = tv / ((1 + wacc) ** years)

    total_pv = sum(pv_fcfs) + pv_tv
    dcf_per_share = total_pv / shares

    info("PV(FCFs)",       f"$ {sum(pv_fcfs)/1e6:.1f} M")
    info("PV(終值)",       f"$ {pv_tv/1e6:.1f} M")
    info("企業價值",       f"$ {total_pv/1e6:.1f} M")
    info("DCF 每股合理價", f"$ {dcf_per_share:.2f}")

    return {
        "method":    "DCF",
        "fair_value": dcf_per_share,
        "wacc":      wacc,
        "g_short":   g_short,
    }


# ──────────────────────────────────────────────
# 3. P/E 估價模組
# ──────────────────────────────────────────────
def calc_pe_valuation(data: dict) -> dict | None:
    """
    P/E 估價：使用 Trailing EPS × 歷史合理 P/E
    """
    section("P/E 估價計算")

    eps = data["trailing_eps"] or data["forward_eps"]
    if not eps or eps <= 0:
        warn("EPS 數據無效，跳過 P/E 估價")
        return None

    trailing_pe = data["trailing_pe"]
    forward_pe  = data["forward_pe"]
    sector      = data["sector"]

    # 按產業給定合理 P/E 區間基準
    sector_pe_map = {
        "Technology":           (22, 35),
        "Consumer Cyclical":    (18, 28),
        "Consumer Defensive":   (16, 24),
        "Financial Services":   (10, 18),
        "Healthcare":           (18, 28),
        "Industrials":          (15, 22),
        "Basic Materials":      (12, 20),
        "Energy":               (10, 16),
        "Utilities":            (14, 20),
        "Real Estate":          (20, 35),
        "Communication Services":(15, 25),
    }
    pe_lo, pe_hi = sector_pe_map.get(sector, (15, 25))

    # 若有歷史P/E，混合使用
    if trailing_pe and 5 < trailing_pe < 200:
        # 合理P/E = 歷史P/E 與 產業基準 各50%
        reasonable_pe = (trailing_pe * 0.5 + (pe_lo + pe_hi) / 2 * 0.5)
    else:
        reasonable_pe = (pe_lo + pe_hi) / 2

    # 成長調整：PEG 概念 - 成長率高者給較高P/E
    g = max(data["earnings_growth"], 0)
    if g > 0.20:
        reasonable_pe *= 1.15
    elif g < 0.05:
        reasonable_pe *= 0.90

    pe_fair = eps * reasonable_pe
    pe_low  = eps * pe_lo
    pe_high = eps * pe_hi

    info("EPS (TTM)",       f"$ {eps:.4f}")
    info("產業 P/E 區間",   f"{pe_lo} ~ {pe_hi}")
    info("採用合理 P/E",    f"{reasonable_pe:.1f}")
    info("P/E 估價低端",    f"$ {pe_low:.2f}")
    info("P/E 合理價",      f"$ {pe_fair:.2f}")
    info("P/E 估價高端",    f"$ {pe_high:.2f}")

    return {
        "method":    "P/E",
        "fair_value": pe_fair,
        "pe_low":    pe_low,
        "pe_high":   pe_high,
        "reasonable_pe": reasonable_pe,
    }


# ──────────────────────────────────────────────
# 4. 動態加權與安全邊際
# ──────────────────────────────────────────────
def dynamic_weighting(data: dict, dcf_result: dict | None, pe_result: dict | None) -> dict | None:
    """
    根據股票特性動態調配 DCF / P/E 權重
    """
    section("動態加權估價")

    if dcf_result is None and pe_result is None:
        warn("DCF 與 P/E 皆無有效結果，無法估價")
        return None

    sector       = data["sector"]
    market_cap   = data["market_cap"]
    g            = data["earnings_growth"]
    fcf_valid    = dcf_result is not None
    pe_valid     = pe_result  is not None

    # 初始權重
    w_dcf, w_pe = 0.5, 0.5

    # 規則1：高成長股（>15%）→ 提高P/E比重
    if g > 0.15:
        w_pe  += 0.15
        w_dcf -= 0.15

    # 規則2：大市值穩定股 (>100B) → 提高DCF比重
    if market_cap > 1e11:
        w_dcf += 0.10
        w_pe  -= 0.10

    # 規則3：產業特性
    high_growth_sectors = {"Technology", "Consumer Cyclical", "Communication Services"}
    stable_sectors      = {"Utilities", "Consumer Defensive", "Financial Services", "Energy"}
    if sector in high_growth_sectors:
        w_pe  += 0.10
        w_dcf -= 0.10
    elif sector in stable_sectors:
        w_dcf += 0.10
        w_pe  -= 0.10

    # 規則4：若某方法無效，全權重給有效方法
    if not fcf_valid:
        w_dcf, w_pe = 0.0, 1.0
    elif not pe_valid:
        w_dcf, w_pe = 1.0, 0.0
    else:
        # 正規化
        total = w_dcf + w_pe
        w_dcf /= total
        w_pe  /= total

    info("DCF 權重",  f"{w_dcf*100:.1f}%")
    info("P/E 權重",  f"{w_pe*100:.1f}%")

    # 加權合理價
    fair = 0.0
    if fcf_valid:
        fair += w_dcf * dcf_result["fair_value"]
    if pe_valid:
        fair += w_pe  * pe_result["fair_value"]

    mos_10 = fair * 0.90   # 10% 安全邊際
    mos_20 = fair * 0.80   # 20% 安全邊際

    return {
        "fair_value": fair,
        "mos_10":     mos_10,
        "mos_20":     mos_20,
        "w_dcf":      w_dcf,
        "w_pe":       w_pe,
    }


# ──────────────────────────────────────────────
# 5. 技術面：移動平均支撐壓力
# ──────────────────────────────────────────────
def calc_technical_levels(data: dict) -> dict:
    """
    計算 MA20 / MA60 / MA200 與量能密集區支撐壓力
    """
    section("技術面分析（壓力 / 支撐）")

    hist = data["hist"]
    if hist is None or hist.empty:
        warn("無歷史價格數據")
        return {}

    close  = hist["Close"]
    volume = hist["Volume"]

    # 移動平均
    ma20  = close.rolling(20).mean().iloc[-1]  if len(close) >= 20  else None
    ma60  = close.rolling(60).mean().iloc[-1]  if len(close) >= 60  else None
    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

    current = data["current_price"]

    # 近期高低點（60日）
    hi_60 = close.tail(60).max()
    lo_60 = close.tail(60).min()

    # 成交量加權平均價（VWAP-like 密集區）
    # 用最近30天計算量能重心
    recent = hist.tail(30).copy()
    recent["typical"] = (recent["High"] + recent["Low"] + recent["Close"]) / 3
    vol_weighted_price = (recent["typical"] * recent["Volume"]).sum() / recent["Volume"].sum()

    # 整理支撐/壓力
    levels = {}
    for name, val in [("MA20", ma20), ("MA60", ma60), ("MA200", ma200),
                      ("60日高點", hi_60), ("60日低點", lo_60),
                      ("量能重心(30日)", vol_weighted_price)]:
        if val is not None and not np.isnan(val):
            levels[name] = float(val)

    # 分類：高於當前價 → 壓力；低於 → 支撐
    resistance = {k: v for k, v in sorted(levels.items(), key=lambda x: x[1]) if v > (current or 0)}
    support    = {k: v for k, v in sorted(levels.items(), key=lambda x: x[1], reverse=True) if v <= (current or 0)}

    print(f"\n  Current Price: $ {current:.2f}" if current else "")
    print(f"\n  {Color.RED}[+] Resistance Levels{Color.RESET}")
    for name, val in resistance.items():
        dist = (val - current) / current * 100 if current else 0
        print(f"    {name:<20} $ {val:.2f}  (+{dist:.1f}%)")

    print(f"\n  {Color.GREEN}[-] Support Levels{Color.RESET}")
    for name, val in support.items():
        dist = (current - val) / current * 100 if current else 0
        print(f"    {name:<20} $ {val:.2f}  (-{dist:.1f}%)")

    return {"resistance": resistance, "support": support}


# ──────────────────────────────────────────────
# 6. 最終輸出彙整
# ──────────────────────────────────────────────
def print_summary(data: dict, weighted: dict | None, tech: dict):
    header("[Report] 估價分析彙整報告")

    current = data["current_price"]
    info("股票代碼",    data["ticker"])
    info("當前股價",    f"$ {current:.2f}" if current else "N/A")

    if weighted:
        fair  = weighted["fair_value"]
        mos10 = weighted["mos_10"]
        mos20 = weighted["mos_20"]

        info("加權合理估價",       f"$ {fair:.2f}")
        info("10% 安全邊際買入價", f"$ {mos10:.2f}")
        info("20% 安全邊際買入價", f"$ {mos20:.2f}")

        if current:
            upside = (fair - current) / current * 100
            if upside < -15:
                tag = "[高估]"
            elif upside < 0:
                tag = "[略高]"
            elif upside > 15:
                tag = "[低估]"
            else:
                tag = "[合理]"
            info("潛在空間",   f"{upside:+.1f}%  {tag}")
            if current <= mos20:
                rec = "[Buy] 具吸引力"
            elif current <= fair:
                rec = "[Hold] 接近合理"
            else:
                rec = "[Watch] 高於合理價，觀察"
            info("評估建議", rec)

    # 技術面摘要
    if tech:
        resistance = tech.get("resistance", {})
        support    = tech.get("support", {})
        r_vals = list(resistance.values())
        s_vals = list(support.values())
        if r_vals:
            info("最近壓力", f"$ {min(r_vals):.2f}  ({list(resistance.keys())[list(resistance.values()).index(min(r_vals))]})")
        if s_vals:
            info("最近支撐", f"$ {max(s_vals):.2f}  ({list(support.keys())[list(support.values()).index(max(s_vals))]})")

    print(f"\n{Color.CYAN}{'='*55}{Color.RESET}\n")


# ──────────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────────
def main():
    header("AI 金融估價分析系統  v1.0  (階段一)")
    ticker = input(f"\n{Color.BOLD}請輸入股票代碼（例：AAPL / 2330.TW）：{Color.RESET}").strip().upper()
    if not ticker:
        print("未輸入代碼，結束。")
        return

    try:
        data     = fetch_stock_data(ticker)
        dcf      = calc_dcf(data)
        pe       = calc_pe_valuation(data)
        weighted = dynamic_weighting(data, dcf, pe)
        tech     = calc_technical_levels(data)
        print_summary(data, weighted, tech)
    except Exception as e:
        print(f"\n{Color.RED}錯誤：{e}{Color.RESET}")
        raise


if __name__ == "__main__":
    main()
