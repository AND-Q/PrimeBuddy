import time

import streamlit as st
from agent.study_supervisor import StudyCopilotSupervisor

st.set_page_config(page_title="PrimeBuddy", page_icon="📚")

st.title("PrimeBuddy")
st.caption("你的智能学习伙伴｜当前场景：408 考研学习")
st.divider()

# 在 session_state 中复用 Supervisor，避免每次页面刷新都重新初始化专家 Agent。
if "agent" not in st.session_state:
    st.session_state["agent"] = StudyCopilotSupervisor()

if "user_id" not in st.session_state:
    st.session_state["user_id"] = "demo_user"

# 初始化聊天记录，并提供一条开场白说明当前支持的学习场景。
if "message" not in st.session_state:
    st.session_state["message"] = [
        {
            "role": "assistant",
            "content": "你好，我是 PrimeBuddy。当前我可以帮你做 408 知识问答、学习计划、错题分析和学习周报。你可以直接问我一个知识点，或者让我根据你的情况制定复习计划。",
        }
    ]

# Streamlit 每次交互都会重新执行脚本，因此需要先把历史消息重新渲染出来。
for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

prompt = st.chat_input("请输入你的问题或需求...")

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    response_messages = []
    with st.spinner("PrimeBuddy 正在思考中..."):
        # 通过 Supervisor 流式调用后端 Agent，并由路由逻辑分发到对应专家。
        res_stream = st.session_state["agent"].execute_stream(prompt, user_id=st.session_state["user_id"])

        def capture(generator, cache_list):
            # 同步缓存完整回复，便于流式展示结束后写回聊天历史。
            for chunk in generator:
                cache_list.append(chunk)

                for char in chunk:
                    time.sleep(0.01)
                    yield char

        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))
        st.session_state["message"].append({"role": "assistant", "content": "".join(response_messages).strip()})
        st.rerun()
