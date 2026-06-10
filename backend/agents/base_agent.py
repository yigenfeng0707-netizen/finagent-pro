import asyncio
from typing import Optional, Dict, Any, Callable
from langchain_openai import ChatOpenAI
from crewai import Agent
import os
from dotenv import load_dotenv
from models.schemas import AgentMessage, AgentRole, AgentStatus
from datetime import datetime

load_dotenv()


class BaseAgent:
    def __init__(self, use_backup: bool = False):
        self.llm = self._create_llm(use_backup)
        self._tools: Dict[str, Callable] = {}
        self.agent: Optional[Agent] = None

    def register_tool(self, name: str, fn: Callable):
        self._tools[name] = fn

    async def call_tool(self, name: str, **kwargs) -> Any:
        fn = self._tools.get(name)
        if not fn:
            return {"error": f"未知工具: {name}"}
        return await asyncio.to_thread(fn, **kwargs)

    def _create_llm(self, use_backup: bool = False) -> ChatOpenAI:
        if use_backup:
            return ChatOpenAI(
                model=os.getenv("BACKUP_MODEL", "glm-4-plus"),
                api_key=os.getenv("ZHIPU_API_KEY"),
                base_url=os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4/"),
                max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
                temperature=float(os.getenv("TEMPERATURE", "0.7"))
            )
        return ChatOpenAI(
            model=os.getenv("DEFAULT_MODEL", "deepseek-chat"),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
            max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
            temperature=float(os.getenv("TEMPERATURE", "0.7"))
        )

    def create_agent(self, role: str, goal: str, backstory: str, tools: Optional[list] = None) -> Agent:
        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=self.llm,
            tools=tools or [],
            verbose=True,
            allow_delegation=False,
            memory=True
        )

    async def run_llm(self, prompt: str) -> str:
        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.ainvoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"LLM调用失败: {str(e)}"

    def make_message(self, agent_name: str, role: AgentRole, content: str,
                     status: AgentStatus = AgentStatus.COMPLETED,
                     confidence: float = 0.0,
                     data: Optional[Dict] = None,
                     thinking: Optional[str] = None) -> AgentMessage:
        return AgentMessage(
            agent=agent_name,
            role=role,
            content=content,
            status=status,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            confidence=confidence,
            data=data,
            thinking=thinking
        )
