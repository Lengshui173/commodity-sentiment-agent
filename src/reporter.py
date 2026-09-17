"""报告生成模块。

生成情感 vs 价格双轴图与 Markdown 简报。
"""

import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")  # 无显示环境下使用 Agg 后端

import matplotlib.pyplot as plt
import pandas as pd

# 中文字体与负号显示
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _plot_sentiment_vs_price(stats: dict, price_df: pd.DataFrame, output_dir: str) -> str:
    """生成情感 vs 价格双轴图，返回图片路径；数据不足返回空字符串。

    Args:
        stats: compute_stats 的输出字典。
        price_df: 价格 DataFrame（含 date、close 列）。
        output_dir: 输出目录。

    Returns:
        图片路径；数据不足时返回 ""。
    """
    trend = stats.get("daily_trend", [])

    # 提取价格 (MM-DD, close)
    price_pairs = []
    if price_df is not None and not price_df.empty and {"date", "close"}.issubset(price_df.columns):
        dates = pd.to_datetime(price_df["date"], errors="coerce").dt.strftime("%m-%d")
        closes = price_df["close"].astype(float)
        price_pairs = [(d, float(c)) for d, c in zip(dates, closes) if isinstance(d, str)]

    if len(trend) < 2 or len(price_pairs) < 2:
        print("[reporter] 情感或价格数据不足（少于 2 条），跳过情感 vs 价格图")
        return ""

    # 合并日期轴（取并集，按 MM-DD 排序）
    trend_map = {d: s for d, s in trend}
    price_map = {d: c for d, c in price_pairs}
    all_dates = sorted(set(trend_map) | set(price_map))
    sent_vals = [trend_map.get(d) for d in all_dates]
    price_vals = [price_map.get(d) for d in all_dates]

    fig, ax1 = plt.subplots()
    # 左轴：平均情感分（蓝）
    ax1.plot(all_dates, sent_vals, marker="o", color="blue", label="平均情感分")
    ax1.set_xlabel("日期")
    ax1.set_ylabel("平均情感分", color="blue")
    ax1.tick_params(axis="y", labelcolor="blue")
    ax1.axhline(0, color="gray", linestyle="--", linewidth=1)  # y=0 参考虚线

    # 右轴：收盘价（橙）
    ax2 = ax1.twinx()
    ax2.plot(all_dates, price_vals, marker="o", color="orange", label="收盘价")
    ax2.set_ylabel("收盘价", color="orange")
    ax2.tick_params(axis="y", labelcolor="orange")

    # 合并图例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")

    fig.suptitle("情感 vs 价格")
    path = os.path.join(output_dir, "sentiment_vs_price.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _clean_cell(value) -> str:
    """清理表格单元格：转字符串、去换行、转义竖线。"""
    return str(value).replace("\n", " ").replace("|", "\\|").strip()


def _top_rows(df: pd.DataFrame, label: str, ascending: bool) -> list[str]:
    """生成 Top 3 表格行。

    Args:
        df: 含 sentiment_label 等列的 DataFrame。
        label: "bullish" 或 "bearish"。
        ascending: 排序方向（bullish 降序、bearish 升序）。

    Returns:
        Markdown 表格行字符串列表。
    """
    sub = (
        df[df["sentiment_label"] == label]
        .sort_values("sentiment_score", ascending=ascending)
        .head(3)
    )
    rows = []
    for _, r in sub.iterrows():
        title = _clean_cell(r.get("title", ""))
        source = _clean_cell(r.get("source", ""))
        score = float(r.get("sentiment_score", 0.0))
        cat = _clean_cell(r.get("event_category", ""))
        rows.append(f"| {title} | {source} | {score:.2f} | {cat} |")
    return rows


def _image_md(path: str, alt: str, filename: str) -> str:
    """生成图片引用；无图时返回占位提示。"""
    if path:
        return f"![{alt}]({filename})"
    return "> 图表未生成（数据不足）"


def _build_judgment(avg: float, top_events: list[tuple]) -> str:
    """基于统计结果生成 AI 综合研判文案。"""
    if avg > 0.2:
        first = "市场情绪偏乐观，关注供给端持续收紧的可能性"
    elif avg < -0.2:
        first = "市场情绪偏悲观，警惕需求走弱带来的下行压力"
    else:
        first = "市场情绪中性，多空因素交织，建议观望"
    dominant = top_events[0][0] if top_events else "其他"
    return f"{first}。{dominant}是本期主导因素。"


def generate_report(
    keyword: str,
    df: pd.DataFrame,
    stats: dict,
    charts: dict,
    price_df: pd.DataFrame,
    output_dir: str = "outputs",
) -> str:
    """生成 Markdown 简报并保存，返回文件路径。

    Args:
        keyword: 商品关键词。
        df: 含情感分析结果的 DataFrame。
        stats: compute_stats 的输出字典。
        charts: generate_charts 的输出字典（含 pie/bar/line）。
        price_df: 价格 DataFrame。
        output_dir: 输出目录，默认 "outputs"。

    Returns:
        生成的 Markdown 文件路径。
    """
    os.makedirs(output_dir, exist_ok=True)

    now = datetime.now()
    report_date = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    total = stats.get("total", len(df))
    dist = stats.get("sentiment_distribution", {})
    avg = stats.get("avg_sentiment_score", 0.0)
    event_counts = stats.get("event_category_counts", {})

    # 时间范围
    time_range = "N/A"
    if not df.empty and "published_at" in df.columns:
        dates = pd.to_datetime(df["published_at"], errors="coerce")
        if dates.notna().any():
            time_range = f"{dates.min().strftime('%Y-%m-%d')} 至 {dates.max().strftime('%Y-%m-%d')}"

    # 情感 vs 价格图
    price_path = _plot_sentiment_vs_price(stats, price_df, output_dir)

    # 主要事件类别 Top 3
    top_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    lines = []
    lines.append(f"# {keyword} 舆情简报 — {report_date}")
    lines.append("")
    lines.append("> 数据来源：GDELT 新闻 + DeepSeek 情感分析 + yfinance 价格")
    lines.append(f"> 生成时间：{timestamp}")
    lines.append("")
    lines.append("## 一、概览")
    lines.append("")
    lines.append(f"- 监测新闻总数：{total} 条")
    lines.append(f"- 时间范围：{time_range}")
    lines.append(
        f"- 情感分布：利多 {dist.get('bullish', 0)} 条 / "
        f"利空 {dist.get('bearish', 0)} 条 / 中性 {dist.get('neutral', 0)} 条"
    )
    lines.append(f"- 平均情感分：{avg}（-1 极度利空，+1 极度利多）")
    lines.append("")
    lines.append("## 二、关键发现")
    lines.append("")
    lines.append("### 利多 Top 3")
    lines.append("")
    lines.append("| 标题 | 来源 | 情感分 | 事件类别 |")
    lines.append("|---|---|---|---|")
    lines += _top_rows(df, "bullish", ascending=False)
    lines.append("")
    lines.append("### 利空 Top 3")
    lines.append("")
    lines.append("| 标题 | 来源 | 情感分 | 事件类别 |")
    lines.append("|---|---|---|---|")
    lines += _top_rows(df, "bearish", ascending=True)
    lines.append("")
    lines.append("### 主要事件类别")
    lines.append("")
    for cat, cnt in top_events:
        lines.append(f"- {cat}：{cnt} 条")
    lines.append("")
    lines.append("## 三、情感趋势")
    lines.append("")
    lines.append(_image_md(charts.get("line"), "情感趋势", "trend_line.png"))
    lines.append("")
    lines.append("## 四、关键词分布")
    lines.append("")
    lines.append(_image_md(charts.get("bar"), "关键词 Top10", "keyword_bar.png"))
    lines.append("")
    lines.append("## 五、情感 vs 价格")
    lines.append("")
    lines.append(_image_md(price_path, "情感 vs 价格", "sentiment_vs_price.png"))
    lines.append("")
    lines.append("## 六、AI 综合研判")
    lines.append("")
    lines.append(_build_judgment(avg, top_events))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本报告由大宗商品舆情监测与价格分析 Agent 自动生成，仅供参考，不构成投资建议。*")

    content = "\n".join(lines)

    filename = f"report_{keyword}_{now.strftime('%Y%m%d')}.md"
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return path
