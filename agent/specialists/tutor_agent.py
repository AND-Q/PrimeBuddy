from langchain.agents import create_agent
from model.factory import get_chat_model
from agent.tools.record_tools import DEMO_USER_ID
from utils.prompt_loader import load_tutor_prompts
from agent.tools.study_tools import search_learning_knowledge
from agent.tools.middleware import monitor_tool, log_before_model


class TutorAgent:
    # 负责 408 知识讲解、考法总结和例题分析等教学类问题。
    def __init__(self):
        self.agent = create_agent(
            model=get_chat_model(),
            system_prompt=load_tutor_prompts(),
            tools=[search_learning_knowledge],
            middleware=[monitor_tool, log_before_model],
        )

    def execute(self, query: str, user_id: str = DEMO_USER_ID) -> str:
        # LangChain Agent 统一使用 messages 结构接收用户输入。
        input_dict = {
            "messages": [
                {"role": "user", "content": f"当前演示用户ID是：{user_id}。调用任何用户相关工具时必须使用这个 user_id。\n\n用户问题：{query}"},
            ]
        }
        result = self.agent.invoke(input_dict)
        return result["messages"][-1].content.strip()

    def execute_stream(self, query: str, user_id: str = DEMO_USER_ID):
        # LangChain Agent 统一使用 messages 结构接收用户输入。
        input_dict = {
            "messages": [
                {"role": "user", "content": f"当前演示用户ID是：{user_id}。调用任何用户相关工具时必须使用这个 user_id。\n\n用户问题：{query}"},
            ]
        }

        final_content = ""
        for chunk in self.agent.stream(input_dict, stream_mode="values"):
            latest_message = chunk["messages"][-1]
            tool_calls = getattr(latest_message, "tool_calls", None)
            if latest_message.type == "ai" and latest_message.content and not tool_calls:
                final_content = latest_message.content.strip()

        if final_content:
            yield final_content + "\n"
