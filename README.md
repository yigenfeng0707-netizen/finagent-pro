# FinAgent Pro - 多Agent智能投顾系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

> 基于国产大模型的多Agent智能投顾系统 | **AFAC2026 金融智能创新大赛 方向四: 前沿技术 - Agentic AI**

---

## 项目简介

FinAgent Pro 是一个专为港股投资者打造的 **多Agent智能投顾系统**。系统模拟专业投研团队的工作流程，通过 **编排器(Orchestrator) + 四位AI专家** 链式协作 —— 市场分析 → 情绪扫描 → 风险评估 → 组合建议 —— 实现 **"感知→推理→行动"** 的自主智能闭环。

### 核心特性

- **真正多Agent链式协作**：Orchestrator编排 → Agent间真实信息传递 → 流式推送思考过程
- **自主智能体闭环**：任务拆解 → 工具调用 → 链式推理 → 综合决策
- **国产技术栈**：DeepSeek/智谱GLM，完全自主可控
- **港股特色**：专注港股市场，AKShare实时数据
- **零成本运行**：开源技术栈，无API调用费用
- **WebSocket实时推送**：前端实时展示Agent思考过程

---

## 比赛信息

| 项目 | 内容 |
|------|------|
| **大赛名称** | AFAC2026 金融智能创新大赛 |
| **参赛方向** | 方向四：前沿技术 - Agentic AI |
| **核心命题** | 基于大语言模型与多智能体协同技术，打造能够自主规划、决策并执行复杂金融任务的"数字员工" |
| **团队** | [你的团队名] |

---

## 系统架构

```
用户请求 (自然语言)
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│                   Agent Orchestrator (编排器)                  │
│  意图识别 → 任务拆解 → 链式调度 → 上下文传递 → 结果综合      │
└──────────────────────────────────────────────────────────────┘
      │
      ├── Step 1 ──► 市场分析师 (MarketAnalyst)
      │               ├─ 工具: get_stock_price / get_technical_indicators
      │               └─ 输出: 技术面分析报告
      │
      ├── Step 2 ──► 情绪扫描器 (SentimentScanner)
      │               ├─ 工具: get_stock_price / RSI情绪映射
      │               └─ 输出: 市场情绪评分
      │
      ├── Step 3 ──► 风险经理 (RiskManager)
      │               ├─ 工具: get_portfolio_risk / calculate_var
      │               └─ 输出: VaR + 风险评估
      │
      └── Step 4 ──► 组合顾问 (PortfolioAdvisor)
                      └─ 输出: 综合资产配置方案
                            │
                            ▼
                    WebSocket → 前端实时展示
                    (Agent思考过程流式推送)
```

---

## 项目结构

```
finagent-pro/
├── backend/
│   ├── agents/                  # 4个专业Agent + 基类
│   │   ├── base_agent.py        # 基类: LLM + 工具注册
│   │   ├── market_analyst.py    # 市场分析师 (重写: 真实LLM输出)
│   │   ├── risk_manager.py      # 风险经理 (重写: 真实LLM+V@R)
│   │   ├── portfolio_advisor.py # 组合顾问 (重写: 真实LLM配置)
│   │   └── sentiment_scanner.py # 情绪扫描器 (重写: 真实LLM分析)
│   ├── models/
│   │   └── schemas.py           # 统一数据模型 (新增)
│   ├── tools/
│   │   └── market_tools.py      # Agent工具库 (新增)
│   ├── memory/
│   │   └── session_memory.py    # 会话记忆系统 (新增)
│   ├── orchestrator.py          # Agent编排器 (新增: 核心)
│   ├── websocket_manager.py     # WebSocket流式推送 (新增)
│   ├── knowledge/
│   │   └── finance_kb.py        # RAG金融知识库
│   ├── services/
│   │   └── market_data.py       # AKShare数据服务
│   ├── main.py                  # FastAPI入口 (重写: 删除所有mock)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # React主应用 (待更新)
│   │   ├── charts/              # ECharts图表组件
│   │   └── ...
│   └── package.json
├── docker-compose.yml           # 容器编排 (新增)
├── Dockerfile.backend           # 后端镜像 (新增)
├── Dockerfile.frontend          # 前端镜像 (新增)
└── README.md
```

---

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- 8GB+ RAM

### 方式一: 本地启动

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env  # 编辑填入API密钥
python main.py

# 前端 (另一个终端)
cd frontend
npm install
npm start
```

### 方式二: Docker 启动

```bash
docker-compose up --build
```

访问 http://localhost:3000

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/orchestrate` | 多Agent链式协作分析（核心） |
| POST | `/api/chat` | 自然语言对话入口 → 自动编排 |
| POST | `/api/stock/analyze` | 单只股票分析 |
| POST | `/api/portfolio/create` | 创建投资组合 |
| POST | `/api/risk/analyze` | 风险分析 |
| GET | `/api/market/stock/{symbol}` | 股票历史数据 |
| GET | `/api/market/hk-spot` | 港股实时行情 |
| GET | `/api/market/hot` | 热门股票 |
| GET | `/api/knowledge/query` | 金融知识库 |
| WS | `/ws/{session_id}` | WebSocket实时推送Agent思考 |

---

## 环境变量

```env
# 必须配置 (至少一个)
DEEPSEEK_API_KEY=your_key_here    # 主模型
ZHIPU_API_KEY=your_key_here       # 备选模型

# 可选
FINNHUB_API_KEY=your_key_here     # 新闻数据
```

---

## 多Agent协作流程

```ascii
用户: "帮我分析腾讯控股"
       │
       ▼
  Orchestrator 拆解任务
       │
       ├── Step 1: 市场分析师
       │   • 调用AKShare获取00700实时数据
       │   • 计算MA5/MA20/MA60/MACD/RSI/布林带
       │   • LLM生成技术面分析报告
       │   → 输出传递到Step 2
       │
       ├── Step 2: 情绪扫描器
       │   • 基于RSI和价格数据映射情绪指数
       │   • LLM生成市场情绪分析
       │   → 输出传递到Step 3
       │
       ├── Step 3: 风险经理
       │   • 计算组合VaR(95%)和波动率
       │   • LLM综合市场数据生成风险评估
       │   → 输出传递到Step 4
       │
       └── Step 4: 组合顾问
           • 结合前三步分析生成最终方案
           • 输出: 投资建议+配置比例+收益预期
```

---

## 创新亮点

1. **Orchestrator编排的链式多Agent协作** — Agent之间真实信息传递，不是模拟对话
2. **自主智能体闭环** — 感知(数据获取)→推理(LLM分析)→行动(综合建议)
3. **Agent工具注册机制** — 每个Agent可动态注册和调用工具函数
4. **WebSocket流式推送** — 前端实时看到每个Agent的"思考过程"
5. **国产自主可控** — 全链路可在国内网络环境运行，无需VPN

---

## 致谢

- AFAC2026 金融智能创新大赛
- [DeepSeek](https://platform.deepseek.com)
- [智谱AI](https://open.bigmodel.cn)
- [AKShare](https://www.akshare.xyz)
- [CrewAI](https://github.com/joaomdmoura/crewAI)

---

<p align="center">
  <strong>FinAgent Pro - 让AI成为每个投资者的专业顾问</strong>
  <br />
  <strong>AFAC2026 方向四: Agentic AI</strong>
</p>
