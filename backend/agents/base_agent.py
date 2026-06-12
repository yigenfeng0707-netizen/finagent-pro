import asyncio
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from crewai import Agent
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from loguru import logger
from models.schemas import AgentMessage, AgentRole, AgentStatus

load_dotenv()


class BaseAgent:
    def __init__(self, use_backup: bool = False):
        self.llm = self._create_llm(use_backup)
        self._tools: Dict[str, Callable] = {}
        self.agent: Optional[Agent] = None
        self._backup_llm = None
        self._backup_llm_ready = False

    def register_tool(self, name: str, fn: Callable):
        self._tools[name] = fn

    async def call_tool(self, name: str, **kwargs) -> Any:
        fn = self._tools.get(name)
        if not fn:
            return {"error": f"未知工具: {name}"}
        return await asyncio.to_thread(fn, **kwargs)

    def _create_llm(self, use_backup: bool = False) -> ChatOpenAI:
        if use_backup:
            api_key = os.getenv("ZHIPU_API_KEY") or "sk-test-placeholder"
            return ChatOpenAI(
                model=os.getenv("BACKUP_MODEL", "glm-4-plus"),
                api_key=api_key,
                base_url=os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4/"),
                max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
                temperature=float(os.getenv("TEMPERATURE", "0.7")),
            )
        api_key = os.getenv("DEEPSEEK_API_KEY") or "sk-test-placeholder"
        return ChatOpenAI(
            model=os.getenv("DEFAULT_MODEL", "deepseek-chat"),
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
            max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
        )

    def _get_backup_llm(self) -> ChatOpenAI:
        if not self._backup_llm_ready:
            self._backup_llm = self._create_llm(use_backup=True)
            self._backup_llm_ready = True
        return self._backup_llm

    def create_agent(self, role: str, goal: str, backstory: str, tools: Optional[list] = None) -> Agent:
        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=self.llm,
            tools=tools or [],
            verbose=True,
            allow_delegation=False,
            memory=True,
        )

    async def run_llm(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        last_error = None

        # Try primary LLM with retry
        for attempt in range(3):
            try:
                response = await asyncio.wait_for(self.llm.ainvoke(messages), timeout=60)
                return response.content if hasattr(response, "content") else str(response)
            except asyncio.TimeoutError:
                last_error = "LLM响应超时(60s)"
                logger.warning(f"LLM调用超时 (attempt {attempt + 1}/3)")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM调用失败 (attempt {attempt + 1}/3): {e}")

            if attempt < 2:
                await asyncio.sleep(2**attempt)  # 1s, 2s

        # Fallback to backup LLM
        logger.warning("主模型全部重试失败，切换备选模型")
        try:
            backup = self._get_backup_llm()
            response = await asyncio.wait_for(backup.ainvoke(messages), timeout=60)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error(f"备选模型也失败: {e}")
            return f"LLM调用失败: 主模型({last_error}), 备选模型({e})"

    def make_message(
        self,
        agent_name: str,
        role: AgentRole,
        content: str,
        status: AgentStatus = AgentStatus.COMPLETED,
        confidence: float = 0.0,
        data: Optional[Dict] = None,
        thinking: Optional[str] = None,
    ) -> AgentMessage:
        return AgentMessage(
            agent=agent_name,
            role=role,
            content=content,
            status=status,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            confidence=confidence,
            data=data,
            thinking=thinking,
        )
