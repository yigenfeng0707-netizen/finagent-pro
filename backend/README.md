# FinAgent Pro - 多Agent智能投顾系统

## 项目概述

基于CrewAI多Agent架构的智能投顾系统，融合市场分析、风险评估、资产配置、情绪分析四大专业Agent，为投资者提供专业级的投资决策支持。

## 技术栈

- **Agent框架**: CrewAI + LangChain
- **LLM**: DeepSeek V3（主力）/ 智谱GLM-4（备选）
- **后端**: FastAPI
- **金融数据**: AKShare（港股/美股/A股）
- **新闻数据**: Finnhub API
- **向量数据库**: Chroma

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑.env文件，填入你的API Key
```

### 3. 启动服务

```bash
python main.py
```

服务将在 http://localhost:8000 启动

API文档: http://localhost:8000/docs

## API接口

### 对话接口
- `POST /api/chat` - 智能投顾对话

### 投资组合
- `POST /api/portfolio/create` - 创建投资组合

### 股票分析
- `POST /api/stock/analyze` - 分析单只股票
- `GET /api/market/hk-spot` - 港股实时行情
- `GET /api/market/us-spot` - 美股实时行情

### 风险分析
- `POST /api/risk/analyze` - 分析投资组合风险

## 四大Agent

1. **Market Analyst** - 市场分析Agent
2. **Risk Manager** - 风险管理Agent
3. **Portfolio Advisor** - 资产配置Agent
4. **Sentiment Scanner** - 情绪分析Agent

## 项目结构

```
backend/
├── agents/              # Agent核心逻辑
│   ├── base_agent.py
│   ├── market_analyst.py
│   ├── risk_manager.py
│   ├── portfolio_advisor.py
│   └── sentiment_scanner.py
├── main.py              # FastAPI入口
├── requirements.txt
└── .env.example
```

## 许可证

MIT License
