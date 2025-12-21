"""
顶级AI AGENT基类，所有智能体继承自此类。
"""
from abc import ABC, abstractmethod

class AgentBase(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, *args, **kwargs):
        pass
