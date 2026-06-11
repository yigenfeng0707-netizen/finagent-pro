# Changelog

## [2.0.0] - 2026-06-12

### 重大更新 — 多Agent协作架构重构

**新增**
- Agent Orchestrator 编排器：4位AI专家链式协作（市场分析→情绪扫描→风险评估→组合建议）
- Agent DAG 决策溯源可视化：ECharts Graph 实时展示Agent间数据流
- 一键演示模式：预设参数 + 性能指标摘要（耗时/工具调用/Agent数）
- RAG知识库集成：ChromaDB语义搜索为每个Agent注入领域知识
- 多维度情绪分析：RSI + 资金流向 + 价格变化三维加权恐惧贪婪指数
- 协方差矩阵组合风险计算 + CVaR(条件风险价值) + 夏普比率
- LLM容错降级：60s超时 + 3次指数退避重试 + 主备模型自动切换
- WebSocket心跳保活 + 连接数限制
- X-Request-ID请求追踪中间件
- JWT认证 + 自定义异常体系
- 沉浸式分析过程动画遮罩
- StockListPage 实时行情数据
- K线图买卖信号标注（止盈/止损线）
- 成交量柱状图红绿着色
- Nginx安全头(CSP/X-Frame-Options) + gzip压缩
- Docker非root用户 + .dockerignore

**修复**
- Orchestrator回调泄漏改为session_id级Dict管理
- 异步事件循环阻塞改用ainvoke + asyncio.to_thread
- 路径穿越漏洞增加session_id正则校验
- WebSocket无限重连改为指数退避策略
- HTTP/WebSocket竞态条件修复
- 前端假数据替换为真实API数据
- ECharts组件生命周期修复（初始化一次+setOption更新）

**安全**
- 移除Docker镜像中的.env嵌入
- 关闭PostgreSQL/Redis端口外部暴露
- Redis密码认证
- 请求参数Pydantic校验（min_length/gt/Literal）
- Agent异常不再泄露完整堆栈

## [1.0.0] - 2026-06-09

### 初始版本
- 单Agent港股分析系统
- AKShare数据接入
- FastAPI后端 + React前端
- 基础技术指标计算
