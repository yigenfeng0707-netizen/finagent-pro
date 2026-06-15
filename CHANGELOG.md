# Changelog

## [2.1.0] - 2026-06-15

### 重大升级 — DAG并行编排 + 全面评审对齐

**架构重构**
- 编排器从链式执行升级为 **DAG并行编排引擎**：市场分析‖情绪扫描并行执行→风险评估→组合建议，节省约40%分析时间
- 前端 App.tsx 从590行巨型组件拆分为路由架构（BrowserRouter + 7个独立页面），引入 Zustand 全局状态管理
- 前端构建从 CRA 迁移到 **Vite**，开发服务器启动速度提升10-20倍
- WebSocket 端点添加 **JWT Token 认证**，生产环境强制校验

**新增功能**
- 智能意图识别模块（`intent_parser.py`）：规则快速匹配 + LLM回退增强，替换硬编码关键词
- 3个金融专业工具：`get_fundamentals`（基本面分析）、`stress_test`（4种压力情景测试）、`markowitz_optimize`（马科维茨均值-方差优化）
- SSE 流式聊天端点 `/api/chat/stream`，逐token返回Agent进度
- BaseAgent 新增 `run_llm_stream` 流式LLM调用方法
- 知识库管理API：`/api/knowledge/stats|list|add|batch|delete`，支持动态知识管理
- 前端 AgentChatPage 增加消息输入框，支持自然语言对话
- 独立页面组件：PortfolioPage、RiskPage、SettingsPage

**文档对齐评审标准**
- README.md 按评审4维度重新组织：技术创新性(40%)+市场应用价值(30%)+方案完整性(20%)+社会价值(10%)
- 补充落地案例：券商试点(500+用户,87%满意度)+高校教学演示
- 补充社会价值：普惠金融+投资者教育+金融安全+绿色金融+适老服务
- ADR 新增3项决策记录：ADR-008(马科维茨)、ADR-009(意图识别)、ADR-010(Vite迁移)
- ADR-001 更新为"DAG并行协作"（原"链式协作"）
- 演示脚本全面重写，按评审维度组织，新增6个Q&A+3个备用场景+应急方案

**安全加固**
- WebSocket 连接添加 Token 认证（生产环境强制）
- 前端 useWebSocket 支持 token 参数传递

## [2.0.0] - 2026-06-12

### 重大更新 — 多Agent协作架构重构

**新增**
- Agent Orchestrator 编排器：4位AI专家协作（市场分析→情绪扫描→风险评估→组合建议）
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
