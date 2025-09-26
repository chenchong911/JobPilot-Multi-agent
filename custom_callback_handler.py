from typing import Any
from langchain_community.callbacks import StreamlitCallbackHandler
from streamlit.external.langchain.streamlit_callback_handler import (
    StreamlitCallbackHandler,
    LLMThought,
)
from langchain.schema import AgentAction


class CustomStreamlitCallbackHandler(StreamlitCallbackHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_sequence = []  # 记录agent执行顺序
        
    def write_agent_name(self, name: str):
        self._parent_container.write(name)
        # 记录agent执行顺序
        self.agent_sequence.append(name)
        
    def get_agent_sequence(self):
        return self.agent_sequence
        
    def clear_agent_sequence(self):
        self.agent_sequence = []
        
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        # 显示agent正在执行的动作
        tool_name = action.tool
        tool_input = action.tool_input
        self._parent_container.write(f"🔧 正在执行: {tool_name}")
        return super().on_agent_action(action, **kwargs)