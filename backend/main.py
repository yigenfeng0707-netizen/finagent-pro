import asyncio
import os
import uuid
from contextlib import asynccontextmanager

import pandas as pd
import sqlalchemy as db
import uvicorn
from auth.routes import router as auth_router
from dotenv import load_dotenv
from exception_handlers import AgentExecutionError, DataFetchError, setup_exception_handlers
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from knowledge.finance_kb import FinanceKnowledgeBase
from loguru import logger
from middleware import RateLimitMiddleware
from models.schemas import (
    ChatRequest,
    OrchestratorRequest,
    OrchestratorResponse,
    PortfolioRequest,
    RiskAnalysisRequest,
    StockAnalysisRequest,
)
from orchestrator import AgentOrchestrator
from services.market_data import MarketDataService
from websocket_manager import WebSocketManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    from auth.jwt import validate_jwt_config
    from database import Base, get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # JWT密钥安全校验
    validate_jwt_config()
    # 启动WebSocket心跳任务
    heartbeat_task = asyncio.create_task(ws_manager.start_heartbeat(interval=30))
    logger.info("WebSocket 心跳检测已启动 (间隔30s)")
    yield
    # 优雅关闭
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()


load_dotenv()

ENV = os.getenv("ENV", "development")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,https://finagent.example.com"
).split(",")

app = FastAPI(
    title="FinAgent Pro - AFAC2026",
    description="多Agent智能投顾系统 | AFAC2026金融智能创新大赛 方向四: Agentic AI",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if ENV != "production" else None,
    redoc_url="/redoc" if ENV != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-API-Key"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)

app.add_middleware(RateLimitMiddleware)

app.include_router(auth_router)
setup_exception_handlers(app)

market_service = MarketDataService()
finance_kb = FinanceKnowledgeBase()
orchestrator = AgentOrchestrator()
ws_manager = WebSocketManager()


async def optional_auth(request: Request):
    """演示模式可选认证，生产环境强制认证"""
    if os.getenv("ENV", "development") == "production":
        from auth.jwt import verify_token

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="需要认证")
        token = auth_header.split(" ", 1)[1]
        payload = verify_token(token)
        if not payload:
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="Token无效或已过期")
        return payload
    return None  # 开发/演示模式跳过认证


# ========== WebSocket端点 ==========


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)


# ========== REST API ==========


@app.get("/")
async def root():
    return {
        "name": "FinAgent Pro",
        "version": "2.0.0",
        "description": "多Agent智能投顾系统 - AFAC2026 方向四: Agentic AI",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    db_ok, redis_ok = True, True
    try:
        from database import get_session_maker

        async with get_session_maker()() as sess:
            await sess.execute(db.text("SELECT 1"))
    except Exception:
        db_ok = False

    try:
        import redis.asyncio as aioredis

        r = await aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "version": "2.0.0",
        "env": os.getenv("ENV", "development"),
        "checks": {
            "database": "ok" if db_ok else "fail",
            "redis": "ok" if redis_ok else "fail",
            "chromadb": "ok" if finance_kb._collection is not None else "lazy",
        },
    }


@app.post("/api/orchestrate", response_model=OrchestratorResponse)
async def orchestrate(request: OrchestratorRequest, auth=Depends(optional_auth)):
    """
    多Agent协作分析入口

    接收用户请求 → Orchestrator拆解任务 → 链式调用4个Agent → 返回综合报告
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        agent_messages = []

        async def on_message(msg):
            await ws_manager.broadcast(session_id, msg)

        orchestrator.on_progress(session_id, on_message)

        try:
            async for msg in orchestrator.run(
                symbols=request.symbols,
                investment_amount=request.investment_amount,
                risk_preference=request.risk_preference,
                market=request.market,
                session_id=session_id,
            ):
                agent_messages.append(msg)
        finally:
            orchestrator.remove_progress(session_id)

        context = _build_sync_context(agent_messages, request)
        report = orchestrator.synthesize_report(context)

        await ws_manager.broadcast_final(session_id, report.model_dump())

        return OrchestratorResponse(status="success", data=report)

    except Exception as e:
        return OrchestratorResponse(status="error", error=f"分析失败: {type(e).__name__}")


def _build_sync_context(agent_messages, request):
    from models.schemas import AgentContext

    ctx = AgentContext(
        user_input=f"分析{'/'.join(request.symbols)}",
        symbols=request.symbols,
        risk_preference=request.risk_preference,
        investment_amount=request.investment_amount,
        market=request.market,
    )
    for msg in agent_messages:
        role = msg.role if hasattr(msg, "role") else ""
        if role:
            ctx.results[f"{role}_analysis"] = msg
    return ctx


@app.post("/api/chat")
async def chat(request: ChatRequest, auth=Depends(optional_auth)):
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
                "例如: 分析腾讯、阿里怎么样、帮我看看美团",
            }

        risk_pref = "moderate"
        if any(w in msg for w in ["保守", "稳健"]):
            risk_pref = "conservative"
        elif any(w in msg for w in ["进取", "激进"]):
            risk_pref = "aggressive"

        agent_messages = []

        async def on_message(msg):
            await ws_manager.broadcast(session_id, msg)

        orchestrator.on_progress(session_id, on_message)

        try:
            async for agent_msg in orchestrator.run(
                symbols=symbols, investment_amount=100000, risk_preference=risk_pref, market="hk", session_id=session_id
            ):
                agent_messages.append(agent_msg)
        finally:
            orchestrator.remove_progress(session_id)

        from types import SimpleNamespace

        req_obj = SimpleNamespace(symbols=symbols, risk_preference=risk_pref, investment_amount=100000, market="hk")
        ctx = _build_sync_context(agent_messages, req_obj)
        report = orchestrator.synthesize_report(ctx)
        await ws_manager.broadcast_final(session_id, report.model_dump())

        return {"type": "analysis_complete", "session_id": session_id, "data": report.model_dump()}

    except Exception as e:
        raise AgentExecutionError("chat", str(e))


@app.post("/api/stock/analyze")
async def analyze_stock(request: StockAnalysisRequest, auth=Depends(optional_auth)):
    """单只股票快速分析"""
    if not request.symbol:
        raise HTTPException(status_code=400, detail="股票代码不能为空")
    try:
        agent = orchestrator.market_analyst
        result = await agent.analyze(symbol=request.symbol, market=request.market)
        return {"success": True, "data": result.data, "analysis": result.content}
    except Exception as e:
        raise AgentExecutionError("market_analyst", str(e))


@app.post("/api/portfolio/create")
async def create_portfolio(request: PortfolioRequest, auth=Depends(optional_auth)):
    """创建投资组合"""
    try:
        result = await orchestrator.portfolio_advisor.advise(
            risk_profile=request.risk_profile,
            investment_amount=request.investment_amount,
            investment_horizon=request.investment_horizon,
        )
        return {"success": True, "portfolio": result.data, "recommendation": result.content}
    except Exception as e:
        raise AgentExecutionError("portfolio_advisor", str(e))


@app.post("/api/risk/analyze")
async def analyze_risk(request: RiskAnalysisRequest, auth=Depends(optional_auth)):
    """风险分析"""
    try:
        result = await orchestrator.risk_manager.analyze(symbols=request.portfolio)
        return {"success": True, "risk_data": result.data, "analysis": result.content}
    except Exception as e:
        raise AgentExecutionError("risk_manager", str(e))


@app.get("/api/market/stock/{symbol}")
async def get_stock_history(symbol: str, market: str = "hk", days: int = 180):
    """获取股票历史数据"""
    try:
        df = await asyncio.to_thread(market_service.get_stock_history, symbol, market, days=days)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="股票数据未找到")
        indicators = market_service.calculate_technical_indicators(df)  # modifies df in-place, returns Dict summary
        data = {
            "dates": (
                df["日期"].dt.strftime("%Y-%m-%d").tolist()
                if "日期" in df.columns
                else df.index.strftime("%Y-%m-%d").tolist()
            ),
            "prices": df["收盘"].tolist() if "收盘" in df.columns else df["close"].tolist(),
            "volumes": df["成交量"].tolist() if "成交量" in df.columns else df["volume"].tolist(),
        }
        for col in ["MA5", "MA10", "MA20", "MA60"]:
            if col in df.columns:
                data[col.lower()] = [None if pd.isna(v) else round(float(v), 2) for v in df[col].tolist()]
        data["indicators"] = indicators
        return {"status": "success", "symbol": symbol, "market": market, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise DataFetchError("market_data", str(e))


@app.get("/api/market/hk-spot")
async def get_hk_spot():
    """港股实时行情"""
    try:
        import akshare as ak

        df = await asyncio.to_thread(ak.stock_hk_spot_em)
        stocks = df.head(20).to_dict(orient="records")
        return {"success": True, "data": stocks}
    except Exception as e:
        raise DataFetchError("hk_spot", str(e))


@app.get("/api/market/hot")
async def get_hot_stocks(market: str = "hk"):
    """热门股票"""
    try:
        stocks = await asyncio.to_thread(market_service.get_hot_stocks, market)
        return {"status": "success", "market": market, "data": stocks}
    except Exception as e:
        raise DataFetchError("hot_stocks", str(e))


@app.get("/api/knowledge/query")
async def query_knowledge(query: str, top_k: int = 3):
    """金融知识库查询"""
    try:
        results = finance_kb.query_knowledge(query, top_k)
        return {"status": "success", "query": query, "results": results}
    except Exception as e:
        raise DataFetchError("knowledge_base", str(e))


# ========== 启动 ==========
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info("FinAgent Pro v2.0.0 启动中... (AFAC2026 方向四: Agentic AI)")
    logger.info(f"服务地址: http://{host}:{port}")
    logger.info(f"API文档: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)
