# FinAgent Pro - 多Agent智能投顾系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

> 🚀 基于国产大模型的港股AI投资助手 | 2026 HK Physical AI Hackathon 参赛项目

---

## 📖 项目简介

FinAgent Pro 是一个专为港股投资者打造的多Agent智能投顾系统。系统模拟专业投研团队的工作流程，通过四位AI专家（市场分析师、风险经理、组合顾问、情绪扫描器）协同工作，为投资者提供专业的投资建议和风险评估。

### ✨ 核心特性

- **🤖 多Agent协作**：四位AI专家各司其职，模拟专业投研团队
- **🇨🇳 国产技术栈**：基于DeepSeek/智谱GLM，完全自主可控
- **📊 港股特色**：专注港股市场，支持港股通、窝轮、牛熊证
- **🧠 RAG增强**：23+金融知识条目，提供专业解释
- **💰 零成本运行**：开源技术栈，无API调用费用
- **🔒 隐私保护**：本地部署，数据不上云

---

## 🎯 功能特性

### 1. 智能选股
- AI分析港股行情
- 提供买入/卖出/持有建议
- 技术指标自动计算（MA、MACD、RSI、布林带）

### 2. 风险评估
- 实时计算投资组合VaR
- 波动率分析
- 风险等级可视化仪表盘

### 3. 资产配置
- 根据风险偏好生成个性化方案
- 动态再平衡建议
- 投资组合可视化

### 4. 情绪监控
- 市场情绪指数追踪
- 舆情监控
- 极端行情预警

### 5. 知识问答
- RAG技术提供专业投资知识
- 港股特色知识库
- 智能问答交互

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        展示层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   React      │  │  Ant Design  │  │   ECharts    │       │
│  │  TypeScript  │  │   UI组件     │  │   图表库     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        服务层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   FastAPI    │  │   CrewAI     │  │  LangChain   │       │
│  │   后端API    │  │  多Agent框架 │  │   LLM集成    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        数据层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   AKShare    │  │  ChromaDB    │  │    Redis     │       │
│  │  港股数据    │  │   向量库     │  │    缓存      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        AI层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ DeepSeek V3  │  │  智谱GLM-4   │  │  RAG知识库   │       │
│  │  国产大模型  │  │   备选模型   │  │  金融知识    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- 8GB+ RAM

### 1. 克隆项目

```bash
git clone https://github.com/your-org/finagent-pro.git
cd finagent-pro
```

### 2. 启动后端

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入API密钥

python main.py
```

后端服务将在 http://localhost:8000 启动

### 3. 启动前端

```bash
cd frontend
npm install
npm start
```

前端将在 http://localhost:3000 启动

---

## 📸 界面预览

### 投资仪表盘
- 实时市场概览（恒生指数、科技指数）
- K线图和技术指标
- 快速AI分析入口

### 多Agent协作
- 四位AI专家实时对话
- 分析过程可视化
- 推理过程透明化

### 风险评估
- 风险等级仪表盘
- 投资组合配置饼图
- 风险等级说明

---

## 🛠️ 技术栈

### 后端
- **FastAPI** - 高性能异步Web框架
- **CrewAI** - 多Agent协作框架
- **LangChain** - LLM应用开发框架
- **AKShare** - 开源金融数据接口
- **ChromaDB** - 开源向量数据库

### 前端
- **React 18** - 前端框架
- **TypeScript** - 类型安全
- **Ant Design** - UI组件库
- **ECharts** - 专业图表库

### AI模型
- **DeepSeek V3** - 主模型（国产）
- **智谱GLM-4** - 备选模型（国产）

---

## 📚 文档

- [部署指南](./部署指南.md) - 详细的部署说明
- [演示脚本](./演示脚本.md) - 比赛演示流程
- [API文档](http://localhost:8000/docs) - 后端API文档

---

## 🎯 应用场景

### 场景1：新手投资者
小明刚接触港股，不知道如何选择股票。使用FinAgent Pro：
1. 选择感兴趣的股票（如腾讯00700）
2. 设置投资金额和风险偏好
3. 获得AI分析建议和风险提示
4. 学习投资知识（RAG问答）

### 场景2：专业投资者
李经理管理着客户的投资组合，需要：
1. 快速获取多只股票的技术分析
2. 评估组合整体风险
3. 获得再平衡建议
4. 监控市场情绪变化

### 场景3：投资教育
王老师用FinAgent Pro教学生：
1. 展示真实市场数据
2. 解释技术指标含义
3. 演示风险管理方法
4. 互动问答加深理解

---

## 🌟 创新亮点

1. **多Agent协作架构**
   - 模拟专业投研团队工作流程
   - 四位AI专家各司其职
   - 协作决策更加可靠

2. **完全自主可控**
   - 国产大模型（DeepSeek/智谱）
   - 开源技术栈
   - 无需VPN，稳定可靠

3. **零成本运行**
   - AKShare免费数据源
   - ChromaDB开源向量库
   - 无API调用费用

4. **香港特色**
   - 专注港股市场
   - 支持港股通
   - 窝轮、牛熊证支持（开发中）

5. **RAG知识增强**
   - 23+金融知识条目
   - 专业投资术语解释
   - 智能问答交互

---

## 📈 未来规划

### V1.5（3个月内）
- [ ] 美股、A股支持
- [ ] 窝轮、牛熊证分析
- [ ] 更多技术指标

### V2.0（6个月内）
- [ ] 自动交易功能
- [ ] 组合回测系统
- [ ] 移动端App

### V3.0（12个月内）
- [ ] 机构版发布
- [ ] 金融合规认证
- [ ] 券商合作接入

---

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 提交Issue
- 报告Bug
- 提出新功能建议
- 改进文档

### 提交PR
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可协议

本项目采用 [MIT](LICENSE) 许可证。

---

## 🙏 致谢

- [DeepSeek](https://platform.deepseek.com) - 国产大模型支持
- [智谱AI](https://open.bigmodel.cn) - GLM-4模型支持
- [AKShare](https://www.akshare.xyz) - 开源金融数据
- [CrewAI](https://github.com/joaomdmoura/crewAI) - 多Agent框架

---

## 📞 联系我们

- **项目主页**: https://github.com/your-org/finagent-pro
- **问题反馈**: https://github.com/your-org/finagent-pro/issues
- **邮箱**: contact@finagent-pro.com

---

<p align="center">
  <strong>FinAgent Pro - 让AI成为每个投资者的专业顾问</strong>
</p>

<p align="center">
  Made with ❤️ for 2026 HK Physical AI Hackathon
</p>
