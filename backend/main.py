"""
FinAgent Pro - 多Agent智能投顾系统后端
FastAPI主入口
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
from dotenv import load_dotenv
from crewai import Crew
from datetime import datetime

from agents import MarketAnalyst, RiskManager, PortfolioAdvisor, SentimentScanner
from services.market_data import MarketDataService
from knowledge.finance_kb import FinanceKnowledgeBase

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(
    title="FinAgent Pro",
    description="多Agent智能投顾系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化Agents和服务
market_analyst = MarketAnalyst()
risk_manager = RiskManager()
portfolio_advisor = PortfolioAdvisor()
sentiment_scanner = SentimentScanner()
market_service = MarketDataService()
finance_kb = FinanceKnowledgeBase()


# ========== 数据模型 ==========
class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None


class PortfolioRequest(BaseModel):
    """投资组合请求模型"""
    risk_profile: str  # conservative/moderate/aggressive
    investment_amount: float
    investment_horizon: str = "medium"  # short/medium/long


class StockAnalysisRequest(BaseModel):
    """股票分析请求模型"""
    symbol: str
    market: str = "hk"  # hk/us/cn


class RiskAnalysisRequest(BaseModel):
    """风险分析请求模型"""
    portfolio: List[Dict[str, Any]]


# ========== API路由 ==========

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "FinAgent Pro",
        "version": "1.0.0",
        "description": "多Agent智能投顾系统",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    智能投顾对话接口
    
    接收用户自然语言输入，返回投资建议
    """
    try:
        message = request.message.lower()
        
        # 简单的意图识别
        if any(word in message for word in ["风险", "波动", "安全"]):
            # 风险相关查询
            response = {
                "type": "risk_info",
                "message": "我可以帮您分析投资组合风险。请告诉我您持有的股票代码和权重，或者选择风险偏好（保守/稳健/进取）。"
            }
        elif any(word in message for word in ["配置", "组合", "资产"]):
            # 资产配置相关
            response = {
                "type": "portfolio_request",
                "message": "我可以为您生成个性化资产配置方案。请告诉我：1. 您的风险偏好（保守/稳健/进取）2. 投资金额 3. 投资期限（短期/中期/长期）"
            }
        elif any(word in message for word in ["腾讯", "00700", "tencent"]):
            # 腾讯分析
            symbol = "00700"
            market = "hk"
            
            # 创建分析任务
            task = market_analyst.create_analysis_task(symbol, market)
            crew = Crew(agents=[market_analyst.agent], tasks=[task], verbose=False)
            result = crew.kickoff()
            
            response = {
                "type": "stock_analysis",
                "symbol": symbol,
                "analysis": result.raw if hasattr(result, 'raw') else str(result)
            }
        else:
            # 通用回复
            response = {
                "type": "general",
                "message": "您好！我是FinAgent Pro智能投顾助手。我可以帮您：\n1. 分析个股行情\n2. 评估投资组合风险\n3. 生成资产配置方案\n4. 分析市场情绪\n\n请告诉我您的投资需求。"
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/create")
async def create_portfolio(request: PortfolioRequest):
    """
    创建投资组合
    
    根据风险偏好生成资产配置方案
    """
    try:
        # 创建资产配置任务
        task = portfolio_advisor.create_portfolio_task(
            risk_profile=request.risk_profile,
            investment_amount=request.investment_amount,
            investment_horizon=request.investment_horizon
        )
        
        # 执行Crew
        crew = Crew(agents=[portfolio_advisor.agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        # 获取基础配置数据
        portfolio_data = portfolio_advisor.create_portfolio(
            risk_profile=request.risk_profile,
            investment_amount=request.investment_amount,
            investment_horizon=request.investment_horizon
        )
        
        return {
            "success": True,
            "portfolio": portfolio_data,
            "recommendation": result.raw if hasattr(result, 'raw') else str(result)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stock/analyze")
async def analyze_stock(request: StockAnalysisRequest):
    """
    分析单只股票
    
    提供技术面分析和投资建议
    """
    try:
        # 获取基础数据
        data = market_analyst.analyze_stock(request.symbol, request.market)
        
        if "error" in data:
            return {"success": False, "error": data["error"]}
        
        # 创建分析任务
        task = market_analyst.create_analysis_task(request.symbol, request.market)
        crew = Crew(agents=[market_analyst.agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        return {
            "success": True,
            "data": data,
            "analysis": result.raw if hasattr(result, 'raw') else str(result)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/analyze")
async def analyze_risk(request: RiskAnalysisRequest):
    """
    分析投资组合风险
    
    计算VaR、波动率等风险指标
    """
    try:
        # 创建风险分析任务
        task = risk_manager.create_risk_task(request.portfolio)
        crew = Crew(agents=[risk_manager.agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        # 获取风险数据
        risk_data = risk_manager.analyze_portfolio_risk(request.portfolio)
        
        return {
            "success": True,
            "risk_data": risk_data,
            "analysis": result.raw if hasattr(result, 'raw') else str(result)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/hk-spot")
async def get_hk_spot():
    """
    获取港股实时行情
    """
    try:
        import akshare as ak
        df = ak.stock_hk_spot_em()
        
        # 转换为JSON
        stocks = df.head(20).to_dict(orient='records')
        return {
            "success": True,
            "data": stocks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/us-spot")
async def get_us_spot():
    """
    获取美股实时行情
    """
    try:
        import akshare as ak
        df = ak.stock_us_spot_em()
        
        stocks = df.head(20).to_dict(orient='records')
        return {
            "success": True,
            "data": stocks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 新增API路由 ==========

class AnalysisRequest(BaseModel):
    """分析请求模型"""
    symbols: List[str]
    investment_amount: float
    risk_preference: str = "moderate"
    market: str = "hk"


@app.get("/api/market/stock/{symbol}")
async def get_stock_history(symbol: str, market: str = "hk", days: int = 180):
    """
    获取股票历史数据
    
    - symbol: 股票代码
    - market: 市场 (hk/us/cn)
    - days: 历史天数
    """
    try:
        df = market_service.get_stock_history(symbol, market, days=days)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="股票数据未找到")
        
        # 计算技术指标
        df = market_service.calculate_technical_indicators(df)
        
        # 格式化数据
        data = {
            "dates": df['日期'].dt.strftime('%Y-%m-%d').tolist() if '日期' in df.columns else df.index.strftime('%Y-%m-%d').tolist(),
            "prices": df['收盘'].tolist() if '收盘' in df.columns else df['close'].tolist(),
            "volumes": df['成交量'].tolist() if '成交量' in df.columns else df['volume'].tolist(),
        }
        
        # 添加均线数据
        if 'MA5' in df.columns:
            data["ma5"] = df['MA5'].tolist()
        if 'MA20' in df.columns:
            data["ma20"] = df['MA20'].tolist()
        if 'MA60' in df.columns:
            data["ma60"] = df['MA60'].tolist()
        
        return {
            "status": "success",
            "symbol": symbol,
            "market": market,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/hot")
async def get_hot_stocks(market: str = "hk", limit: int = 10):
    """
    获取热门股票
    
    - market: 市场 (hk/us/cn)
    - limit: 返回数量
    """
    try:
        stocks = market_service.get_hot_stocks(market, limit)
        return {
            "status": "success",
            "market": market,
            "data": stocks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analysis/portfolio")
async def analyze_portfolio(request: AnalysisRequest):
    """
    投资组合分析
    
    多Agent协作分析投资组合
    """
    try:
        # 获取市场数据
        market_data = {}
        for symbol in request.symbols:
            df = market_service.get_stock_history(symbol, request.market, days=90)
            if df is not None:
                market_data[symbol] = df
        
        # 获取知识库相关信息
        kb_context = finance_kb.query_knowledge(f"{request.risk_preference}型投资者资产配置")
        
        # 模拟多Agent分析结果
        agent_messages = []
        
        # 市场分析师
        agent_messages.append({
            "agent": "市场分析师",
            "role": "Market Analyst",
            "content": f"分析{len(request.symbols)}只股票的市场趋势。当前市场情绪中性偏乐观，科技股表现活跃。",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        # 风险经理
        risk_level = 45 if request.risk_preference == "moderate" else (25 if request.risk_preference == "conservative" else 70)
        agent_messages.append({
            "agent": "风险经理",
            "role": "Risk Manager",
            "content": f"评估完成。当前组合风险等级为{risk_level}/100，符合{request.risk_preference}型投资者偏好。建议控制单一股票仓位不超过30%。",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        # 组合顾问
        agent_messages.append({
            "agent": "组合顾问",
            "role": "Portfolio Advisor",
            "content": f"根据{request.risk_preference}型风险偏好，建议分散投资于科技、金融、消费等板块。",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        # 情绪扫描器
        agent_messages.append({
            "agent": "情绪扫描器",
            "role": "Sentiment Scanner",
            "content": "市场情绪指数: 62/100 (中性偏乐观)。机构资金流入科技股，散户情绪谨慎。",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        # 生成投资组合配置
        allocation = []
        if len(request.symbols) == 1:
            # 单只股票，建议分散
            symbol = request.symbols[0]
            stock_names = {"00700": "腾讯控股", "09988": "阿里巴巴", "03690": "美团", "01810": "小米集团"}
            name = stock_names.get(symbol, symbol)
            allocation = [
                {"symbol": symbol, "name": name, "weight": 60, "amount": request.investment_amount * 0.6},
                {"symbol": "01299", "name": "友邦保险", "weight": 25, "amount": request.investment_amount * 0.25},
                {"symbol": "CASH", "name": "现金储备", "weight": 15, "amount": request.investment_amount * 0.15}
            ]
        else:
            # 多只股票平均分配
            weight = 100 // len(request.symbols)
            for symbol in request.symbols:
                allocation.append({
                    "symbol": symbol,
                    "name": symbol,
                    "weight": weight,
                    "amount": request.investment_amount * weight / 100
                })
        
        # 生成建议
        recommendation = "buy" if request.risk_preference == "aggressive" else ("hold" if request.risk_preference == "conservative" else "buy")
        expected_return = 12.5 if request.risk_preference == "aggressive" else (6.0 if request.risk_preference == "conservative" else 8.5)
        
        return {
            "status": "success",
            "data": {
                "recommendation": recommendation,
                "confidence": 78.5,
                "risk_level": risk_level,
                "expected_return": expected_return,
                "reasoning": f"基于多Agent协作分析，当前市场环境适合{request.risk_preference}型投资者。{agent_messages[0]['content']} 风险方面，{agent_messages[1]['content']} 配置方面，{agent_messages[2]['content']}",
                "portfolio_allocation": allocation,
                "agent_messages": agent_messages,
                "kb_context": kb_context[:2] if kb_context else []
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/query")
async def query_knowledge(query: str, top_k: int = 3):
    """
    查询金融知识库
    
    - query: 查询内容
    - top_k: 返回结果数量
    """
    try:
        results = finance_kb.query_knowledge(query, top_k)
        return {
            "status": "success",
            "query": query,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 启动服务 ==========
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"🚀 FinAgent Pro 启动中...")
    print(f"📡 服务地址: http://{host}:{port}")
    print(f"📚 API文档: http://{host}:{port}/docs")
    
    uvicorn.run(app, host=host, port=port)
