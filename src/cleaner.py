"""数据清洗模块。

对采集到的新闻数据（collector 输出的 dict 列表）进行清洗：
去重、去缺失、去 HTML/噪声、时间标准化、按时间降序排列。
"""

import re

import pandas as pd


def _clean_text(text: str) -> str:
    """清洗单条文本：去除 HTML 标签、换行/制表符、压缩多余空格。

    Args:
        text: 原始文本。

    Returns:
        清洗后的文本。
    """
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<.*?>", "", text)       # 去除 HTML 标签
    text = re.sub(r"[\r\n\t]+", " ", text)  # 换行/制表符替换为空格
    text = re.sub(r"\s+", " ", text)        # 压缩连续空格为单个空格
    return text.strip()


def clean_news(articles: list[dict]) -> pd.DataFrame:
    """清洗新闻数据，返回清洗后的 DataFrame。

    步骤：
        1. 转为 DataFrame，列名小写。
        2. 按 title 去重（忽略大小写与首尾空格）。
        3. 丢弃 title 或 snippet 为空的记录。
        4. 文本清洗：去 HTML 标签、多余空格、特殊字符。
        5. 时间标准化：published_at 转 datetime，无法解析的丢弃。
        6. 按发布时间降序排列。

    Args:
        articles: collector 输出的原始新闻列表。

    Returns:
        清洗后的 DataFrame。
    """
    # 1. 转 DataFrame，列名小写
    df = pd.DataFrame(articles)
    df.columns = [c.lower() for c in df.columns]
    original_count = len(df)

    # 2. 按 title 去重（忽略大小写与首尾空格）
    df["_title_key"] = df["title"].fillna("").astype(str).str.strip().str.lower()
    df = df.drop_duplicates(subset="_title_key", keep="first").drop(columns="_title_key")
    dedup_count = original_count - len(df)

    # 3. 缺失值处理：title 或 snippet 为空/缺失则丢弃
    before_missing = len(df)
    title_ok = df["title"].fillna("").astype(str).str.strip() != ""
    snippet_ok = df["snippet"].fillna("").astype(str).str.strip() != ""
    df = df[title_ok & snippet_ok]
    missing_count = before_missing - len(df)

    # 4. 文本清洗
    df["title"] = df["title"].astype(str).apply(_clean_text)
    df["snippet"] = df["snippet"].astype(str).apply(_clean_text)

    # 5. 时间标准化：无法解析 → NaT → 丢弃
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
    df = df.dropna(subset=["published_at"])

    # 6. 按发布时间降序排列
    df = df.sort_values("published_at", ascending=False).reset_index(drop=True)

    # 打印清洗统计
    print(f"[cleaner] 原始记录数：{original_count} → 清洗后记录数：{len(df)}")
    print(f"[cleaner] 去重数量：{dedup_count}，缺失值丢弃数量：{missing_count}")

    return df


if __name__ == "__main__":
    # 构造 3 条含重复和缺失的模拟数据
    mock_data = [
        {"title": "OPEC+宣布减产", "snippet": "国际油价上涨", "published_at": "2026-09-15T10:00:00", "source": "a.com", "url": "http://a.com"},
        {"title": "OPEC+宣布减产 ", "snippet": "国际油价上涨", "published_at": "2026-09-15T10:00:00", "source": "a.com", "url": "http://a.com"},
        {"title": "美国原油库存增加", "snippet": "", "published_at": "2026-09-14T10:00:00", "source": "b.com", "url": "http://b.com"},
    ]
    df = clean_news(mock_data)
    print(df)
