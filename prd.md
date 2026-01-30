PRD 1.0: Alpha-Agent 持仓分析专家
3.1 产品定义
一个基于 Agentic 工作流的个人股票投资决策助手，旨在通过深度融合实时市场数据、用户持仓上下文与专业投资框架，提供闭环的风险管理与策略建议。

3.2 核心功能模块
A. 风险扫描仪 (Risk Analysis)
宏观风险: Agent 自动抓取本周重要事件（如 Fed 讲话、CPI），并与用户持仓（如 GOOG、TBEA）的相关性进行交叉比对。

个股集中度: 检测单一板块或单一个股（如你的 GOOG 370 股）是否占比过高。

波动预警: 利用历史波动率（HV）与隐含波动率（IV）的背离，提示潜在的“黑天鹅”或暴雷风险。

B. 决策建议引擎 (Decision Support)
动态仓位管理: 根据凯利公式或马科维茨模型，针对当前市场环境下 BABA、GOOG 等标的提出加减仓建议。

目标价对齐: 结合你对 BABA $200 的目标价，Agent 会持续跟踪基本面是否支撑该逻辑，若支撑减弱，主动建议减仓。

C. 期权对冲实验室 (Options Hedging)
自动策略建议: * 若持仓有大幅浮盈（如你的 BABA Put 盈利），建议平仓离场或进行移仓（Rolling）。

若持仓处于震荡期，建议卖出 Covered Call（正如你之前对 GOOG 的操作）来增强收益。

希腊字母对冲: 监控整体组合的 Delta、Gamma、Vega，建议开立期权头寸以使组合趋向 Delta Neutral。

D. 自动化工作流 (Agentic Workflow)
意图理解: 用户输入“帮我分析一下现在的持仓风险”。

工具调用: Agent 调用 Yahoo Finance 获取价格，调用 Alpha Vantage 获取财报，调用 Reddit/X 获取舆情。

反思与修正 (Self-Reflection): Agent 内部进行推演：“我的建议是否过于激进？如果美联储加息，这个建议还成立吗？”

3.3 交互体验
每日晨报: 早上 8:30 发送推文：“Wang Peng，今天你的 GOOG 持仓面临财报前波动风险，建议将 335 Call 进行 Rolling 或买入 $320 Put 对冲。”

对话式回测: “如果我把所有 BABA 仓位换成 REITs，过去三年的收益曲线会如何？”

4. 其它建议 (Brainstorming Bonus)
多因子情绪分析: 针对你持有的中概股（BABA、特变电工），Agent 可以专门监控微博、雪球以及华尔街对中国资产的情绪指数。

财报智能比对: 当 GOOG 发布财报时，Agent 不仅总结财报，还自动对比你的“人生 K 线”逻辑中对未来的预期是否被证伪。

税务损耗优化: 针对新加坡/美国等不同市场的税务政策，Agent 可以在年底建议卖出亏损头寸来抵税（Tax-loss harvesting）。

REITs 专项逻辑: 既然你对新加坡 REITs 感兴趣，可以加入一个专门计算 DPU (Distribution Per Unit) 和 杠杆率 (Gearing Ratio) 的 Agent 模块。
