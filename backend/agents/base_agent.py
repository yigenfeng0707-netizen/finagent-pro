"""
基础Agent类 - 所有专业Agent的基类
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from crewai import Agent
import os
from dotenv import load_dotenv

load_dotenv()


class BaseAgent:
    """基础Agent类"""
    
    def __init__(self, use_backup: bool = False):
        """
        初始化基础Agent
        
        Args:
            use_backup: 是否使用备选模型（智谱GLM）
        """
        self.llm = self._create_llm(use_backup)
    
    def _create_llm(self, use_backup: bool = False) -> ChatOpenAI:
        """创建LLM实例"""
        if use_backup:
            # 使用智谱GLM作为备选
            return ChatOpenAI(
                model=os.getenv("BACKUP_MODEL", "glm-4-plus"),
                api_key=os.getenv("ZHIPU_API_KEY"),
                base_url=os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4/"),
                max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
                temperature=float(os.getenv("TEMPERATURE", "0.7"))
            )
        else:
            # 使用DeepSeek V3作为主模型
            return ChatOpenAI(
                model=os.getenv("DEFAULT_MODEL", "deepseek-chat"),
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
                max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
                temperature=float(os.getenv("TEMPERATURE", "0.7"))
            )
    
    def create_agent(self, role: str, goal: str, backstory: str, tools: Optional[list] = None) -> Agent:
        """
        创建CrewAI Agent
        
        Args:
            role: Agent角色
            goal: Agent目标
            backstory: Agent背景故事
            tools: Agent工具列表
            
        Returns:
            CrewAI Agent实例
        """
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
