# 架构决策记录 (Architecture Decision Records)

## ADR-001: 链式协作 vs 并行 Agent 执行

**状态**: 已采纳
**日期**: 2025-12

### 背景

多 Agent 系统的执行模式有两种主流方案：链式（Pipeline）和并行（Fan-out/Fan-in）。链式模式中 Agent 按序执行，前一个的输出作为后一个的输入；并行模式中多个 Agent 同时执行后合并结果。

### 决策

采用 **链式协作** 模式：市场分析 → 情绪扫描 → 风险评估 → 组合建议。

### 理由

金融投研场景天然具有信息依赖关系——情绪分析需要市场数据作为输入，风险评估需要综合市场分析和情绪，组合建议需要前三步的全部结果。链式模式保证了信息流的正确性和可追溯性，同时让 WebSocket 实时推送的"思考过程"对用户而言具有清晰的叙事逻辑。并行模式虽然更快，但在当前场景下会导致信息不完整和推理质量下降。

---

## ADR-002: ChromaDB vs FAISS 作为 RAG 向量数据库

**状态**: 已采纳
**日期**: 2025-11

### 背景

RAG 知识库需要一个向量数据库来存储和检索金融知识。主要候选方案是 ChromaDB 和 FAISS。

### 决策

选择 **ChromaDB**。

### 理由

ChromaDB 提供开箱即用的 Python API，支持文本 + 元数据的混合存储，查询接口更友好。FAISS 虽然检索速度更快，但它只是一个向量索引库，需要自行管理 ID 映射、元数据过滤和持久化。对于知识库规模（< 1000 条）的场景，ChromaDB 的性能完全够用，且开发效率显著更高。

---

## ADR-003: DeepSeek vs Qwen 作为主力大模型

**状态**: 已采纳
**日期**: 2025-11

### 背景

国产大模型中，DeepSeek V3 和 Qwen 系列都是优秀的候选方案。

### 决策

采用 **DeepSeek V3 (deepseek-chat)** 为主力模型，**智谱 GLM-4-Plus** 为备选。

### 理由

DeepSeek V3 在金融分析任务上的中文理解能力和推理深度表现优异，API 价格极低（约 Qwen 的 1/3），且支持 64K 上下文窗口，适合需要长上下文的投研场景。智谱 GLM-4-Plus 作为备选模型，在 DeepSeek 不可用时自动切换，保证了系统的高可用性。

---

## ADR-004: 自研 Orchestrator vs CrewAI 框架

**状态**: 已采纳
**日期**: 2025-12

### 背景

CrewAI 是流行的多 Agent 编排框架，但其设计面向通用场景。项目初期曾评估直接使用 CrewAI。

### 决策

采用 **自研 AgentOrchestrator**，同时保留 CrewAI 作为依赖（用于 Agent 基类的工具注册和 LLM 封装）。

### 理由

CrewAI 的 crew.kickoff() 模式是黑盒执行，无法实现 WebSocket 实时推送每个 Agent 的思考过程——这是本项目的核心差异化特性。自研 Orchestrator 支持 async generator（yield 每条消息）、Agent 间显式上下文传递、超时降级和知识库注入，这些功能在 CrewAI 中要么不存在要么需要大量 hack。

---

## ADR-005: FastAPI + WebSocket vs Flask + SSE

**状态**: 已采纳
**日期**: 2025-10

### 背景

后端需要实时推送 Agent 分析进度到前端。候选方案包括 WebSocket（双向通信）和 SSE（Server-Sent Events，单向推送）。

### 决策

选择 **FastAPI + WebSocket**。

### 理由

FastAPI 原生支持 async/await，与 LLM 的异步调用模式天然契合。WebSocket 支持双向通信，未来可扩展为"用户在分析过程中追加提问"的交互模式。FastAPI 的 Pydantic v2 集成让请求验证和序列化更加类型安全。SSE 虽然更简单，但单向通信限制了未来的扩展性。

---

## ADR-006: 协方差矩阵风险计算 vs Monte Carlo 模拟

**状态**: 已采纳
**日期**: 2026-01

### 背景

组合风险评估有两种主流方法：基于协方差矩阵的参数法和 Monte Carlo 模拟法。

### 决策

采用 **协方差矩阵参数法**，计算 VaR、CVaR、夏普比率和年化波动率。

### 理由

参数法计算速度快（毫秒级），适合实时分析场景。Monte Carlo 模拟虽然更灵活，但需要大量采样（> 10000 次）才能收敛，在用户等待分析结果的时间窗口内无法完成。此外，参数法的计算过程可解释性更强——评委可以看到协方差矩阵和权重向量的具体数值，而 Monte Carlo 的结果存在随机性。

---

## ADR-007: Docker Compose 4 服务架构

**状态**: 已采纳
**日期**: 2026-01

### 背景

部署架构需要在简单性和生产就绪之间平衡。

### 决策

采用 4 服务 Docker Compose：**PostgreSQL + Redis + Backend + Frontend (Nginx)**。

### 理由

PostgreSQL 提供持久化存储（用户、分析记录），Redis 提供缓存层（减少重复的 AKShare API 调用），Backend 运行 FastAPI + Agent 逻辑，Frontend 通过 Nginx 反向代理提供静态资源和安全头。这种架构既适合本地开发演示，也接近真实生产环境，展示工程成熟度。
