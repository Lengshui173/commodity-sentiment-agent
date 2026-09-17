"""统计与图表模块。

对情感分析结果进行聚合统计，并生成图表。
"""

import os
import re
from collections import Counter

import matplotlib

matplotlib.use("Agg")  # 无显示环境下使用 Agg 后端

import matplotlib.pyplot as plt
import pandas as pd

# 中文字体与负号显示
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 关键词停用词（oil/crude 为主题词本身，去掉更能体现差异）
_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "have", "has",
    "will", "are", "was", "were", "but", "not", "you", "its", "oil", "crude",
}


def _extract_keywords(df: pd.DataFrame) -> list[tuple[str, int]]:
    """从标题中提取英文关键词 Top 10（不用 jieba）。

    Args:
        df: 含 title 列的 DataFrame。

    Returns:
        [(词, 频次), ...] 列表，按频次降序。
    """
    text = " ".join(df["title"].fillna("").astype(str))
    words = re.findall(r"[A-Za-z]{3,}", text)  # 提取长度 >= 3 的英文单词
    words = [w.lower() for w in words if w.lower() not in _STOPWORDS]
    counter = Counter(words)
    return counter.most_common(10)


def _compute_daily_trend(df: pd.DataFrame) -> list[tuple[str, float]]:
    """按天聚合平均情感分。

    Args:
        df: 含 published_at、sentiment_score 列的 DataFrame。

    Returns:
        [("MM-DD", 平均情感分), ...] 列表，按日期升序。
    """
    dt = pd.to_datetime(df["published_at"], errors="coerce")
    tmp = pd.DataFrame({"date": dt.dt.strftime("%m-%d"), "score": df["sentiment_score"]})
    tmp = tmp.dropna(subset=["date"])
    daily = tmp.groupby("date")["score"].mean().round(4)
    return [(d, float(s)) for d, s in daily.items()]


def compute_stats(df: pd.DataFrame) -> dict:
    """对情感分析结果做聚合统计。

    Args:
        df: analyzer 输出的 DataFrame。

    Returns:
        统计结果字典；输入为空时返回空 dict。
    """
    if df is None or df.empty:
        print("[stats] 输入 DataFrame 为空，返回空字典")
        return {}

    total = len(df)

    # 情感分布（三种标签固定，缺失补 0）
    sentiment_distribution = (
        df["sentiment_label"]
        .value_counts()
        .reindex(["bullish", "bearish", "neutral"], fill_value=0)
        .to_dict()
    )

    avg_sentiment_score = round(float(df["sentiment_score"].mean()), 4)

    event_category_counts = df["event_category"].value_counts().to_dict()

    return {
        "total": total,
        "sentiment_distribution": sentiment_distribution,
        "avg_sentiment_score": avg_sentiment_score,
        "event_category_counts": event_category_counts,
        "top_keywords": _extract_keywords(df),
        "daily_trend": _compute_daily_trend(df),
    }


# ---------- 图表生成 ----------

def _plot_sentiment_pie(dist: dict, output_dir: str) -> str:
    """生成情感分布饼图。"""
    labels = ["bullish", "bearish", "neutral"]
    colors = ["green", "red", "gray"]  # 利多绿、利空红、中性灰
    values = [dist.get(label, 0) for label in labels]

    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
    ax.set_title("情感分布")
    path = os.path.join(output_dir, "sentiment_pie.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_keyword_bar(top_keywords: list[tuple[str, int]], output_dir: str) -> str:
    """生成关键词 Top10 水平条形图。"""
    words = [w for w, _ in top_keywords]
    counts = [c for _, c in top_keywords]

    fig, ax = plt.subplots()
    ax.barh(words, counts, color="steelblue")
    ax.invert_yaxis()  # 频次最高显示在上方
    ax.set_xlabel("频次")
    ax.set_title("关键词 Top10")
    path = os.path.join(output_dir, "keyword_bar.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_trend_line(trend: list[tuple[str, float]], output_dir: str) -> str:
    """生成每日情感趋势折线图。"""
    dates = [d for d, _ in trend]
    scores = [s for _, s in trend]

    fig, ax = plt.subplots()
    ax.plot(dates, scores, marker="o", color="steelblue")
    ax.axhline(0, color="gray", linestyle="--", linewidth=1)  # y=0 参考虚线
    ax.set_xlabel("日期")
    ax.set_ylabel("平均情感分")
    ax.set_title("每日情感趋势")
    path = os.path.join(output_dir, "trend_line.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def generate_charts(stats: dict, output_dir: str = "outputs") -> dict:
    """生成图表并保存到 output_dir。

    Args:
        stats: compute_stats 的输出字典。
        output_dir: 输出目录，默认 "outputs"。

    Returns:
        {"pie": 路径, "bar": 路径, "line": 路径}，跳过未生成的键。
    """
    os.makedirs(output_dir, exist_ok=True)
    charts = {}

    # 饼图：情感分布为空则跳过
    dist = stats.get("sentiment_distribution", {})
    if dist and sum(dist.values()) > 0:
        charts["pie"] = _plot_sentiment_pie(dist, output_dir)
    else:
        print("[stats] 情感分布数据为空，跳过饼图")

    # 条形图：关键词为空则跳过
    top_keywords = stats.get("top_keywords", [])
    if top_keywords:
        charts["bar"] = _plot_keyword_bar(top_keywords, output_dir)
    else:
        print("[stats] 关键词数据为空，跳过条形图")

    # 折线图：趋势少于 2 天则跳过
    trend = stats.get("daily_trend", [])
    if len(trend) >= 2:
        charts["line"] = _plot_trend_line(trend, output_dir)
    else:
        print("[stats] 趋势数据不足（少于 2 天），跳过折线图")

    return charts


if __name__ == "__main__":
    import pandas as pd

    mock_df = pd.DataFrame([
        {"title": "OPEC+宣布维持减产协议，国际油价应声上涨",
         "sentiment_score": 0.70, "sentiment_label": "bullish",
         "event_category": "供给变化", "confidence": 0.90,
         "key_phrase": "OPEC+减产", "published_at": "2026-09-15 10:00:00"},
        {"title": "美国原油库存意外增加，市场担忧需求疲软",
         "sentiment_score": -0.65, "sentiment_label": "bearish",
         "event_category": "库存数据", "confidence": 0.85,
         "key_phrase": "库存增加", "published_at": "2026-09-14 10:00:00"},
        {"title": "国际油价窄幅震荡，市场等待OPEC会议指引",
         "sentiment_score": 0.00, "sentiment_label": "neutral",
         "event_category": "其他", "confidence": 0.60,
         "key_phrase": "等待指引", "published_at": "2026-09-15 15:00:00"},
        {"title": "Middle East tension escalates, oil supply risk rises",
         "sentiment_score": 0.55, "sentiment_label": "bullish",
         "event_category": "地缘政治", "confidence": 0.80,
         "key_phrase": "地缘紧张", "published_at": "2026-09-13 10:00:00"},
        {"title": "Global economy slowdown worries weigh on demand",
         "sentiment_score": -0.50, "sentiment_label": "bearish",
         "event_category": "宏观经济", "confidence": 0.75,
         "key_phrase": "经济放缓", "published_at": "2026-09-13 12:00:00"},
    ])
    stats = compute_stats(mock_df)
    print("统计结果：")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    charts = generate_charts(stats)
    print("生成的图表：", charts)
