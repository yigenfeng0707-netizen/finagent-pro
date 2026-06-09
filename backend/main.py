from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import asyncio
import uuid
from dotenv import load_dotenv

from models.schemas import (
    ChatRequest, StockAnalysisRequest, PortfolioRequest,
    RiskAnalysisRequest, OrchestratorRequest, OrchestratorResponse,
    FinalReport
)
from services.market_data import MarketDataService
from knowledge.finance_kb import FinanceKnowledgeBase
from orchestrator import AgentOrchestrator
from websocket_manager import WebSocketManager

load_dotenv()

app = FastAPI(
    title="FinAgent Pro - AFAC2026",
    description="多Agent智能投顾系统 | AFAC2026金融智能创新大赛 方向四: Agentic AI",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

market_service = MarketDataService()
finance_kb = FinanceKnowledgeBase()
orchestrator = AgentOrchestrator()
ws_manager = WebSocketManager()


# ========== WebSocket端点 ==========

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)


# ========== REST API ==========

@app.get("/")
async def root():
    return {
        "name": "FinAgent Pro",
        "version": "2.0.0",
        "description": "多Agent智能投顾系统 - AFAC2026 方向四: Agentic AI",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/orchestrate", response_model=OrchestratorResponse)
async def orchestrate(request: OrchestratorRequest):
    """
    多Agent协作分析入口
    
    接收用户请求 → Orchestrator拆解任务 → 链式调用4个Agent → 返回综合报告
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        agent_messages = []

        async def on_message(msg):
            await ws_manager.broadcast(session_id, msg)

        orchestrator.on_progress(on_message)

        async for msg in orchestrator.run(
            symbols=request.symbols,
            investment_amount=request.investment_amount,
            risk_preference=request.risk_preference,
            market=request.market
        ):
            agent_messages.append(msg)

        context = _build_sync_context(agent_messages, request)
        report = orchestrator.synthesize_report(context)

        await ws_manager.broadcast_final(session_id, report.model_dump())

        return OrchestratorResponse(status="success", data=report)

    except Exception as e:
        return OrchestratorResponse(status="error", error=str(e))


def _build_sync_context(agent_messages, request):
    from models.schemas import AgentContext
    ctx = AgentContext(
        user_input=f"分析{'/'.join(request.symbols)}",
        symbols=request.symbols,
        risk_preference=request.risk_preference,
        investment_amount=request.investment_amount,
        market=request.market
    )
    for msg in agent_messages:
        role = msg.role if hasattr(msg, 'role') else ""
        if role:
            ctx.results[f"{role}_analysis"] = msg
    return ctx


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """智能对话入口 - 自然语言请求→自动编排Agent"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        msg = request.message.lower()

        if any(w in msg for w in ["腾讯", "00700", "tencent"]):
            symbols = ["00700"]
        elif any(w in msg for w in ["阿里", "09988", "alibaba"]):
            symbols = ["09988"]
        elif any(w in msg for w in ["美团", "03690"]):
            symbols = ["03690"]
        elif any(w in msg for w in ["小米", "01810"]):
            symbols = ["01810"]
        else:
            return {
                "type": "general",
                "session_id": session_id,
                "message": "您好！我是FinAgent Pro智能投顾助手。请告诉我您想分析哪只港股？"
                           "例如: 分析腾讯、阿里怎么样、帮我看看美团"
            }

        risk_pref = "moderate"
        if any(w in msg for w in ["保守", "稳健"]):
            risk_pref = "conservative"
        elif any(w in msg for w in ["进取", "激进"]):
            risk_pref = "aggressive"

        agent_messages = []

        async def on_message(msg):
            await ws_manager.broadcast(session_id, msg)

        orchestrator.on_progress(on_message)

        async for agent_msg in orchestrator.run(
            symbols=symbols,
            investment_amount=100000,
            risk_preference=risk_pref,
            market="hk"
        ):
            agent_messages.append(agent_msg)

        req_obj = type('req', (), {
            'symbols': symbols, 'risk_preference': risk_pref,
            'investment_amount': 100000, 'market': 'hk'
        })()
        ctx = _build_sync_context(agent_messages, req_obj)
        report = orchestrator.synthesize_report(ctx)
        await ws_manager.broadcast_final(session_id, report.model_dump())

        return {
            "type": "analysis_complete",
            "session_id": session_id,
            "data": report.model_dump()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stock/analyze")
async def analyze_stock(request: StockAnalysisRequest):
    """单只股票快速分析"""
    if not request.symbol:
        raise HTTPException(status_code=500, detail="股票代码不能为空")
    try:
        agent = orchestrator.market_analyst
        result = await agent.analyze(symbol=request.symbol, market=request.market)
        return {"success": True, "data": result.data, "analysis": result.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/create")
async def create_portfolio(request: PortfolioRequest):
    """创建投资组合"""
    try:
        result = await orchestrator.portfolio_advisor.advise(
            risk_profile=request.risk_profile,
            investment_amount=request.investment_amount,
            investment_horizon=request.investment_horizon
        )
        return {
            "success": True,
            "portfolio": result.data,
            "recommendation": result.content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/risk/analyze")
async def analyze_risk(request: RiskAnalysisRequest):
    """风险分析"""
    try:
        result = await orchestrator.risk_manager.analyze(symbols=request.portfolio)
        return {
            "success": True,
            "risk_data": result.data,
            "analysis": result.content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/stock/{symbol}")
async def get_stock_history(symbol: str, market: str = "hk", days: int = 180):
    """获取股票历史数据"""
    try:
        df = market_service.get_stock_history(symbol, market, days=days)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="股票数据未找到")
        df = market_service.calculate_technical_indicators(df)
        data = {
            "dates": df['日期'].dt.strftime('%Y-%m-%d').tolist() if '日期' in df.columns else df.index.strftime('%Y-%m-%d').tolist(),
            "prices": df['收盘'].tolist() if '收盘' in df.columns else df['close'].tolist(),
            "volumes": df['成交量'].tolist() if '成交量' in df.columns else df['volume'].tolist(),
        }
        for col in ['MA5', 'MA10', 'MA20', 'MA60']:
            if col in df.columns:
                data[col.lower()] = df[col].tolist()
        return {"status": "success", "symbol": symbol, "market": market, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/hk-spot")
async def get_hk_spot():
    """港股实时行情"""
    try:
        import akshare as ak
        df = ak.stock_hk_spot_em()
        stocks = df.head(20).to_dict(orient='records')
        return {"success": True, "data": stocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/hot")
async def get_hot_stocks(market: str = "hk"):
    """热门股票"""
    try:
        stocks = market_service.get_hot_stocks(market)
        return {"status": "success", "market": market, "data": stocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/query")
async def query_knowledge(query: str, top_k: int = 3):
    """金融知识库查询"""
    try:
        results = finance_kb.query_knowledge(query, top_k)
        return {"status": "success", "query": query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 启动 ==========
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"FinAgent Pro v2.0.0 启动中... (AFAC2026 方向四: Agentic AI)")
    print(f"服务地址: http://{host}:{port}")
    print(f"API文档: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)
