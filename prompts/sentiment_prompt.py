"""DeepSeek 情感分析提示词模块。

负责构建情感打分与事件分类的提示词，要求模型严格输出 JSON。
"""

# 提示词模板：{title} / {snippet} 为占位符，运行时替换
_PROMPT_TEMPLATE = """你是一个专业的金融舆情分析助手。请对以下大宗商品相关新闻进行分析，
严格按照 JSON 格式返回，不要输出任何其他内容，不要加 markdown 代码块。

分析维度：
1. sentiment_score：情感评分，-1（极度利空）到 1（极度利多），0为中性，保留2位小数
2. sentiment_label：情感标签，只能是 "bullish"、"bearish"、"neutral" 之一
3. event_category：事件分类，从以下选择最匹配的一个：
   ["供给变化", "需求变化", "政策监管", "地缘政治", "宏观经济", "库存数据", "其他"]
4. confidence：置信度，0.0 到 1.0，保留2位小数
5. key_phrase：从新闻中提取最能代表核心信息的短语（10字以内，中文）

返回格式示例（严格按此结构，不要有多余字段）：
{"sentiment_score": -0.70, "sentiment_label": "bearish",
 "event_category": "供给变化", "confidence": 0.85,
 "key_phrase": "OPEC+增产"}

新闻标题：{title}
新闻摘要：{snippet}"""


def build_sentiment_prompt(title: str, snippet: str) -> str:
    """构建情感打分与事件分类的提示词。

    将模板中的 {title}、{snippet} 占位符替换为参数值。

    Args:
        title: 新闻标题。
        snippet: 新闻摘要。

    Returns:
        发送给 DeepSeek 的提示词字符串。
    """
    return _PROMPT_TEMPLATE.replace("{title}", title).replace("{snippet}", snippet)
