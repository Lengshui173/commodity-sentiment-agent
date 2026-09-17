"""commodity-sentiment-agent 命令行入口。

用法::

    python main.py "原油"
    python main.py "原油" --max-records 30
"""

import argparse

from src import analyzer, cleaner, collector, price_fetcher, reporter, stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。

    Args:
        argv: 命令行参数列表；默认读取 sys.argv。

    Returns:
        解析后的参数命名空间，包含 keyword、max_records。
    """
    parser = argparse.ArgumentParser(
        prog="commodity-sentiment-agent",
        description="商品情感分析代理：采集新闻、情感打分、生成图表与 Markdown 简报。",
    )
    parser.add_argument(
        "keyword",
        nargs="?",
        default="原油",
        help="商品关键词，默认 '原油'",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=50,
        help="最多采集新闻条数，默认 50",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """程序入口：采集 → 清洗 → 分析 → 统计/图表 → 价格 → 报告。"""
    args = parse_args(argv)
    keyword = args.keyword
    print(f"=== 开始分析：{keyword} ===")

    # 1. 采集
    news, source = collector.fetch_news(keyword, max_records=args.max_records)
    print(f"[main] 采集 {len(news)} 条（来源：{source}）")

    # 2. 清洗
    df = cleaner.clean_news(news)
    if df.empty:
        print("[main] 清洗后无数据，终止")
        return

    # 3. AI 分析
    df = analyzer.analyze_news(df)

    # 4. 统计 + 图表
    stats_result = stats.compute_stats(df)
    charts = stats.generate_charts(stats_result)

    # 5. 价格
    price_df = price_fetcher.fetch_price()

    # 6. 报告
    report_path = reporter.generate_report(keyword, df, stats_result, charts, price_df)
    print(f"=== 完成！报告已保存：{report_path} ===")


if __name__ == "__main__":
    main()
