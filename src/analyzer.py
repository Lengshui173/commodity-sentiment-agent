"""情感分析模块。

使用 DeepSeek API 对清洗后的新闻做情感打分与事件分类，要求严格 JSON 输出。
"""

import json
import os
import time

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from prompts.sentiment_prompt import build_sentiment_prompt

# 加载 .env 中的环境变量
load_dotenv()

# DeepSeek 客户端（OpenAI 兼容接口）
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-chat"

# 兜底值：连续两次分析失败时返回
_FALLBACK = {
    "sentiment_score": 0.0,
    "sentiment_label": "neutral",
    "event_category": "其他",
    "confidence": 0.0,
    "key_phrase": "",
}


def _clip_result(data: dict) -> dict:
    """校验字段并截断数值范围。

    Args:
        data: 模型返回的 JSON 解析结果。

    Returns:
        规范化后的 5 字段 dict。
    """
    # sentiment_score 截断到 [-1, 1]，保留 2 位小数
    try:
        score = round(max(-1.0, min(1.0, float(data.get("sentiment_score", 0.0)))), 2)
    except (TypeError, ValueError):
        score = 0.0
    # confidence 截断到 [0, 1]，保留 2 位小数
    try:
        confidence = round(max(0.0, min(1.0, float(data.get("confidence", 0.0)))), 2)
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "sentiment_score": score,
        "sentiment_label": data.get("sentiment_label", "neutral"),
        "event_category": data.get("event_category", "其他"),
        "confidence": confidence,
        "key_phrase": data.get("key_phrase", ""),
    }


def _analyze_one(title: str, snippet: str) -> dict:
    """对单条新闻调用 DeepSeek 分析，返回情感结果 dict。

    JSON 解析失败时重试 1 次；两次均失败返回兜底值。
    API 错误（如 401/402/网络）不在此捕获，向上抛出。

    Args:
        title: 新闻标题。
        snippet: 新闻摘要。

    Returns:
        含 5 个情感字段的 dict。
    """
    prompt = build_sentiment_prompt(title, snippet)

    for attempt in range(2):  # 首次 + 重试 1 次
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            data = json.loads(content)  # 非 JSON 会抛 JSONDecodeError
            if not isinstance(data, dict):
                raise ValueError("模型返回的不是 JSON 对象")
            return _clip_result(data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"[analyzer] 第 {attempt + 1} 次分析失败：{e}")
            time.sleep(0.5)

    return dict(_FALLBACK)


def analyze_news(df: pd.DataFrame) -> pd.DataFrame:
    """对 DataFrame 中每条新闻调用 DeepSeek 分析，追加情感结果列。

    Args:
        df: 清洗后的新闻 DataFrame（需含 title、snippet 列）。

    Returns:
        追加 sentiment_score / sentiment_label / event_category /
        confidence / key_phrase 五列后的 DataFrame。
    """
    total = len(df)
    results = []
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        results.append(_analyze_one(row["title"], row["snippet"]))
        if i % 5 == 0:
            print(f"[analyzer] 已处理 {i}/{total}")
        time.sleep(0.5)  # 每条之间间隔，避免触发限流

    result_df = pd.DataFrame(results, index=df.index)
    return pd.concat([df, result_df], axis=1)


if __name__ == "__main__":
    import pandas as pd

    mock_df = pd.DataFrame([
        {"title": "OPEC+宣布维持减产协议，国际油价应声上涨", "snippet": "减产延长至年底"},
        {"title": "美国原油库存意外增加，市场担忧需求疲软", "snippet": "库存增幅超预期"},
        {"title": "国际油价窄幅震荡，市场等待OPEC会议指引", "snippet": "投资者保持观望"},
    ])
    result = analyze_news(mock_df)
    print(result[["title", "sentiment_score", "sentiment_label", "event_category", "confidence", "key_phrase"]].to_string())
