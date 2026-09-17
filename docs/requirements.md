# 需求文档：commodity-sentiment-agent

【需求已确认，要点如下】

- 输入商品关键词，默认“原油”
- 用 requests 直接调用 GDELT Doc API，抓取最近 7 天最多 50 条新闻
- pandas 清洗去重、去噪、标准化
- DeepSeek API 做情感打分 + 事件分类，严格 JSON 输出
- yfinance 拉取 CL=F 最近 7 天收盘价，作为可选增强
- 生成图表：情感分布饼图、关键词 Top10 条形图、情感趋势折线图、情感 vs 价格双轴图
- 生成 Markdown 简报
- 命令行运行：`python main.py "原油"`
- 明确不做：Web UI、实时流、交易信号、付费数据源
