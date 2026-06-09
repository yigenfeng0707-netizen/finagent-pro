from celery import shared_task
from tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_agent_analysis(self, symbols: list, amount: float, risk: str, market: str, user_id: str):
    import asyncio
    from orchestrator import AgentOrchestrator
    from models.schemas import AgentContext

    async def _run():
        orch = AgentOrchestrator()
        results = []
        async for msg in orch.run(symbols=symbols, investment_amount=amount,
                                  risk_preference=risk, market=market):
            results.append(msg.model_dump())

        ctx = AgentContext(
            user_input=f"分析{'/'.join(symbols)}",
            symbols=symbols,
            risk_preference=risk,
            investment_amount=amount,
            market=market,
        )
        for msg in results:
            role = msg.get("role", "")
            if role:
                ctx.results[f"{role}_analysis"] = msg
        report = orch.synthesize_report(ctx)
        return {
            "status": "completed",
            "report": report.model_dump(),
            "messages": results,
        }

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task
def send_price_alert(user_email: str, symbol: str, alert_type: str, current_price: float):
    from services.notification import send_email_alert
    send_email_alert(user_email, symbol, alert_type, current_price)
    return {"sent_to": user_email, "symbol": symbol}
