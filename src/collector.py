"""新闻采集模块。

使用 requests 直接调用 GDELT DOC 2.0 API，抓取指定商品关键词的新闻。
GDELT Doc API 免费、无需 Key。

策略：代理优先 + 降级模拟。
  1. 优先通过本地代理（127.0.0.1:7897）真实请求 GDELT。
  2. 真实请求失败或结果为空时，降级为生成模拟新闻数据。
"""

import time
from datetime import datetime, timedelta, timezone

import requests
import urllib3

# verify=False 会触发 InsecureRequestWarning，这里关闭以保持输出干净
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# GDELT DOC 2.0 API 基础地址
BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# 请求头：GDELT 要求携带 User-Agent
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SentimentAgent/1.0)"}

TIMEOUT = 15        # 单次请求超时（秒）
MAX_RETRIES = 2     # 失败后重试次数
RETRY_DELAY = 3     # 重试间隔（秒）

# 本地代理（科学上网）
PROXY = "http://127.0.0.1:7897"


def _build_query(keyword: str) -> str:
    """构建 query 参数。

    GDELT 对含空格的关键词要求用引号包裹，例如 query='"crude oil"'。

    Args:
        keyword: 原始关键词。

    Returns:
        处理后的 query 值。
    """
    kw = keyword.strip()
    if " " in kw:
        return f'"{kw}"'
    return kw


def _parse_seendate(seendate: str) -> str:
    """将 GDELT seendate 解析为 ISO 格式。

    GDELT 返回的 seendate 形如 "20240915T120000Z"，
    解析为 ISO 字符串 "2024-09-15T12:00:00"。

    Args:
        seendate: GDELT 原始时间字段。

    Returns:
        ISO 格式时间字符串；无法解析时原样返回。
    """
    if not seendate:
        return ""
    raw = seendate.rstrip("Z")
    date_part = raw[:8]    # 20240915
    time_part = raw[9:15]  # 120000（跳过中间的 T）
    if len(date_part) == 8 and len(time_part) == 6:
        return (
            f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            f"T{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
        )
    return seendate


def _normalize_record(article: dict) -> dict:
    """将 GDELT 单条文章记录规范化为统一格式。

    Args:
        article: GDELT 返回的原始文章 dict。

    Returns:
        规范化后的记录 dict。
    """
    title = (article.get("title") or "").strip() or "（无标题）"
    snippet = (article.get("snippet") or "").strip() or title
    return {
        "title": title,
        "url": article.get("url", ""),
        "source": article.get("domain", ""),
        "published_at": _parse_seendate(article.get("seendate", "")),
        "snippet": snippet,
    }


def _request_articles(params: dict, proxies: dict) -> list[dict]:
    """单次请求 GDELT 并解析 JSON，返回 articles 列表。

    Args:
        params: 查询参数字典。
        proxies: 代理配置字典。

    Returns:
        文章列表。

    Raises:
        requests.RequestException: 网络或 HTTP 错误。
        ValueError: 返回体非合法 JSON。
    """
    resp = requests.get(
        BASE_URL,
        params=params,
        headers=HEADERS,
        timeout=TIMEOUT,
        proxies=proxies,
        verify=False,  # 避免 SSL 证书校验问题
    )
    resp.raise_for_status()
    # GDELT 有时返回非 JSON（如 HTML 错误页），这里解析失败会抛 ValueError
    data = resp.json()
    return data.get("articles") or []


def generate_mock_news(keyword: str, count: int = 10) -> list[dict]:
    """生成模拟新闻数据，用于真实请求失败/为空时的降级。

    标题为纯中文、固定围绕"原油"主题，覆盖利多、利空、中性三类。

    Args:
        keyword: 商品关键词（当前模拟标题固定围绕"原油"，参数保留以备扩展）。
        count: 生成条数，默认 10。

    Returns:
        模拟新闻记录列表。
    """
    _ = keyword  # 保留接口：当前模拟标题固定围绕"原油"，暂未按关键词生成
    # 覆盖利多 / 利空 / 中性三类情绪
    templates = [
        # 利多
        "OPEC+宣布维持减产协议，国际油价应声上涨",
        "中东地缘局势紧张，原油供应面临中断风险",
        "美国原油库存超预期下降，需求前景获提振",
        "美元指数走弱，国际油价创近月新高",
        "国内成品油价格迎来年内第三次上调",
        # 利空
        "美国原油库存意外增加，市场担忧需求疲软",
        "美元指数走强，大宗商品价格普遍承压",
        "全球经济放缓担忧升温，原油需求前景转弱",
        "主要经济体制造业数据疲软，油价遭遇抛售",
        # 中性
        "国际油价窄幅震荡，市场等待 OPEC 会议指引",
        "原油多空因素交织，投资者保持观望",
        "分析师：短期油价方向不明，关注下周库存数据",
    ]
    sources = ["新浪财经", "财联社", "华尔街见闻", "路透中文网", "澎湃新闻"]

    now = datetime.now(timezone.utc)
    news = []
    for i in range(count):
        title = templates[i % len(templates)]
        # 每隔 15 小时一条，分布在近 7 天内
        published = now - timedelta(hours=i * 15)
        news.append(
            {
                "title": title,
                "url": f"https://example.com/news/{i:02d}",
                "source": sources[i % len(sources)],
                "published_at": published.strftime("%Y-%m-%dT%H:%M:%S"),
                "snippet": title,
            }
        )
    return news


def fetch_news(
    keyword: str,
    max_records: int = 50,
    timespan: str = "7d",
) -> tuple[list[dict], str]:
    """抓取新闻：代理优先 + 降级模拟。

    带重试机制：失败重试 MAX_RETRIES 次，间隔 RETRY_DELAY 秒。
    真实请求失败或结果为空时，降级为生成 10 条模拟新闻。

    Args:
        keyword: 商品关键词。
        max_records: 最大返回条数，默认 50。
        timespan: 时间范围，默认 "7d"。

    Returns:
        (新闻记录列表, 数据来源标记)，来源标记为 "真实" 或 "模拟"。
    """
    params = {
        "query": _build_query(keyword),
        "mode": "artlist",
        "maxrecords": max_records,
        "timespan": timespan,
        "format": "json",
        "sort": "datedesc",
    }
    proxies = {"http": PROXY, "https": PROXY}

    articles = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            articles = _request_articles(params, proxies)
            break
        except (requests.RequestException, ValueError) as e:
            print(f"[collector] 请求失败（第 {attempt + 1} 次）：{e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    if articles:
        return [_normalize_record(a) for a in articles], "真实"

    # 降级：真实请求失败或结果为空，切换为模拟数据
    mock_news = generate_mock_news(keyword, count=10)
    print(f"[collector] 未获取到真实新闻，已切换为模拟数据模式（共 {len(mock_news)} 条）")
    return mock_news, "模拟"


if __name__ == "__main__":
    news, source = fetch_news("crude oil", max_records=5)
    print(f"共获取 {len(news)} 条（数据来源：{source}）")
    for n in news[:3]:
        print("-", n["title"], "|", n["source"], "|", n["published_at"])
