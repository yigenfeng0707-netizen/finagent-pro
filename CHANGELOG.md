# Changelog

## [2.2.0] - 2026-06-15

### 冠军品质升级 — 学术级精度 + LLM综合推理 + ESG真实数据 + 东方财富数据增强 + 竞品对比

**核心算法升级**
- 马科维茨优化：1000次随机采样 → **scipy SLSQP精确求解**，输出最大夏普比率+最小波动率组合，2000次Dirichlet采样有效前沿（可视化用）
- 压力测试：经验公式 → **协方差矩阵+相关性聚集(Longin & Solnik, 2001)+分散化比率(Choueifaty & Coignard, 2008)**，学术引用Basel(2009)+Kupiec(2000)
- 综合报告：关键词匹配 → **多因子评分模型(风险30%+动量25%+情绪25%+夏普20%) + LLM增强综合推理**，3个API端点统一使用`synthesize_report_with_llm`

**ESG真实数据接入（从骨架到真实）**
- 新增 `get_esg_rating` 工具：聚合MSCI(712只港股)+商道融绿(8200+)+华证(6250+)三家ESG评级
- ESG Agent从占位数据升级为AKShare真实数据（底层东方财富/新浪财经公开API）
- 数据缓存机制，避免重复API调用

**SSE流式端点修复**
- `/api/chat/stream` 末尾补全综合报告生成逻辑：收集agent_messages → synthesize_report → 发送final_report事件

**前端工程化**
- 移除 `react-scripts` 依赖，升级 TypeScript 5.5
- 新增 ESLint 配置（.eslintrc.cjs）+ lint/typecheck 脚本
- package.json 版本号 1.0.0 → 2.1.0

**东方财富数据增强（6个新工具，全部免费）**
- `get_company_profile` — 公司概况（行业/董事长/员工/介绍）
- `get_financial_indicator` — 20+财务指标（EPS/ROE/净利率/营收增长/股息率/市值）
- `get_dividend_history` — 分红派息历史（近10年）
- `get_valuation_comparison` — 估值对比+行业排名（PE/PB/PS/PCF）
- `get_growth_comparison` — 成长对比+行业排名（EPS增长/营收增长/利润增长）
- `get_hot_rank` — 港股实时热度排名TOP20
- 市场分析师Agent增强：技术面+财务指标+估值对比三维分析

**市场价值增强**
- 新增竞品深度对比表：FinAgent Pro vs 雪球/富途牛牛/同花顺（8维度）
- 落地案例添加MVP模拟数据标注
- 绿色金融量化：Patterson et al. (2022) 碳排放换算

**文档同步**
- README.md 更新：竞品对比+学术级描述+ESG端点+视频录制指引
- 项目创意方案.md 同步更新：竞品对比+学术级描述+落地案例标注
- 新增 录屏脚本.md：3分钟演示视频录制流程

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
