"""价格数据模块（可选增强）。

使用 yfinance 拉取商品标的（默认原油 CL=F）最近 7 天收盘价。
"""

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

# 本地代理（科学上网）
PROXY = "http://127.0.0.1:7897"


def _extract_close(data) -> pd.DataFrame | None:
    """从 yf.download 结果中提取 date + close 两列。

    Args:
        data: yf.download 返回的 DataFrame（可能为空）。

    Returns:
        含 date、close 两列的 DataFrame；无数据时返回 None。
    """
    if data is None or data.empty:
        return None

    # 兼容单级/多级列索引，统一取 Close 列
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]  # 单标的场景取第一列
    else:
        close = data["Close"]

    close = close.dropna()
    if close.empty:
        return None

    df = pd.DataFrame({
        "date": pd.to_datetime(close.index),
        "close": close.astype(float).values,
    })
    return df.sort_values("date").reset_index(drop=True)


def _generate_mock_price() -> pd.DataFrame:
    """生成过去 7 天的模拟原油价格（仅交易日，98-108 区间波动）。"""
    today = datetime.now(timezone.utc).date()
    all_days = [today - timedelta(days=i) for i in range(6, -1, -1)]  # 升序 7 个日历日
    dates = [d for d in all_days if d.weekday() < 5]  # 跳过周六(5)、周日(6)
    # 模拟收盘价：98-108 区间内小幅波动，按交易日数量取对应条数
    closes = [99.2, 100.6, 99.8, 102.1, 103.4, 101.9, 104.5][: len(dates)]
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "close": [float(c) for c in closes],
    })


def fetch_price(keyword: str = "CL=F", period: str = "7d") -> pd.DataFrame:
    """拉取指定标的最近 N 天日线收盘价（代理优先 + 降级模拟）。

    Args:
        keyword: yfinance 标的代码，默认 "CL=F"（WTI 原油期货）。
        period: 时间范围，默认 "7d"。

    Returns:
        含 date（datetime）、close（float）两列的 DataFrame，按日期升序。
    """
    # 设置代理环境变量（yfinance 在国内需走代理）
    os.environ["HTTP_PROXY"] = PROXY
    os.environ["HTTPS_PROXY"] = PROXY

    try:
        data = yf.download(keyword, period=period, progress=False, auto_adjust=True)
    except Exception as e:
        print(f"[price_fetcher] 拉取真实价格失败：{e}")
        data = None

    df = _extract_close(data)
    if df is not None and not df.empty:
        lo = round(float(df["close"].min()), 2)
        hi = round(float(df["close"].max()), 2)
        print(f"[price_fetcher] 已获取 {len(df)} 条真实价格数据，价格范围 {lo}-{hi}")
        return df

    # 降级：请求失败或返回空数据 → 模拟数据
    print("[price_fetcher] 未获取到真实价格数据，已切换为模拟数据（7天）")
    return _generate_mock_price()


if __name__ == "__main__":
    df = fetch_price()
    print(df)
