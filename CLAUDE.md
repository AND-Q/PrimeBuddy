# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

PrimeBuddy 是一个面向中文 408 考研学习场景的 Python Streamlit + LangChain 多 Agent RAG 应用。主要调用链路是：

```text
Streamlit 聊天界面 -> StudyCopilotSupervisor -> 专家 Agent -> LangChain 工具/RAG/本地学习数据 -> 大模型回复
```

项目背景、演示问题和面试讲解内容集中在 [PrimeBuddy.md](PrimeBuddy.md)。这些内容适合作为产品叙事参考；如果文档和代码实现不一致，以当前代码为准。

## 常用命令

项目文档默认使用名为 `agent` 的 conda 环境；如果要和文档中的运行方式保持一致，优先使用 `conda run -n agent <command>`。

```bash
# 安装依赖
pip install -r requirement.txt

# 模型相关环境变量
export MY_API_KEY="your OpenAI-compatible API key"
export MY_BASE_URL="https://your-base-url/v1"
export DASHSCOPE_API_KEY="your DashScope API key"

# 修改 data/408 后，构建或更新 Chroma 知识库索引
conda run -n agent python rag/vector_store.py

# 启动 Streamlit 应用
conda run -n agent streamlit run app.py

# 指定端口启动
conda run -n agent streamlit run app.py --server.port 8502

# Python 语法/编译检查
conda run -n agent python -m compileall app.py agent config model rag utils

# unittest 自动发现；当前没有正式测试文件，可能显示 Ran 0 tests
conda run -n agent python -m unittest discover

# 如果后续新增 unittest 测试，可运行单个测试模块/用例/方法
conda run -n agent python -m unittest path.to.test_module
conda run -n agent python -m unittest path.to.test_module.TestCase.test_method

# 快速确认关键依赖可导入
conda run -n agent python -c "import streamlit, langchain, langgraph, langchain_chroma; print('imports ok')"
```

项目文档中提供的常用烟测：

```bash
# Supervisor 路由烟测：使用 __new__ 避免完整初始化依赖模型的专家 Agent
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from agent.study_supervisor import StudyCopilotSupervisor; s=StudyCopilotSupervisor.__new__(StudyCopilotSupervisor); cases={'请生成我的本周学习报告':'report','这道题我错了帮我分析':'mistake','我每天3小时帮我制定计划':'planner','讲一下虚拟内存':'tutor','你好':'general'}; got={q:s.route(q).route for q in cases}; assert got==cases, got; print('route smoke checks passed')"

# RAG 检索烟测：需要 Embedding 和向量库配置可用
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from rag.vector_store import VectorStoreService; vs=VectorStoreService(); docs=vs.get_retriever().invoke('操作系统 虚拟内存 缺页中断 常见考点'); text='\n'.join(d.page_content for d in docs); assert any(term in text for term in ['虚拟内存','缺页','分页','页面']); print('retrieval smoke checks passed')"
```

当前没有发现 lint、pytest、CI、Docker、Makefile、README、Cursor 规则或 Copilot 指令，也没有正式测试体系。项目文档提到当前环境未安装 `pytest`。

## 架构说明

### 入口与界面

- [app.py](app.py) 是 Streamlit 聊天应用入口。
- 应用把 `StudyCopilotSupervisor` 保存在 `st.session_state["agent"]`，把聊天记录保存在 `st.session_state["message"]`。
- 回复通过 `StudyCopilotSupervisor.execute_stream()` 交给 `st.chat_message(...).write_stream(...)` 展示；当前专家 Agent 会先消费 LangChain values stream 并只 yield 最终文本，`app.py` 再按字符加延迟模拟前端流式效果。

### Supervisor 与路由

- [agent/study_supervisor.py](agent/study_supervisor.py) 中的 `StudyCopilotSupervisor.__init__()` 会一次性初始化四个专家 Agent。
- 路由逻辑是确定性的中文关键词匹配，不是 LLM 分类。
- 路由优先级依次是：周报、错题、学习计划、知识讲解，最后回退到通用回复。
- 路由烟测用 `StudyCopilotSupervisor.__new__()` 调用 `route()`，可以避免 `StudyCopilotSupervisor.__init__()` 一次性创建四个专家 Agent；但导入 `agent.study_supervisor` 仍会导入专家模块和部分 RAG 工具，因此环境变量/依赖缺失时优先检查 import-time 初始化。

### 专家 Agent

专家 Agent 位于 [agent/specialists/](agent/specialists/)，共同模式是：调用 `create_agent(model=chat_model, system_prompt=..., tools=[...], middleware=[monitor_tool, log_before_model])`，并提供 `execute()` 和 `execute_stream()` 方法。

注意：`agent.tools.study_tools` 和 `agent.tools.agent_tools` 在模块导入时会创建全局 `RagSummarizeService`，因此导入 Tutor/Mistake/旧 ReAct 相关模块可能会同时初始化向量库、Embedding 和共享 chat model。

- `TutorAgent`：负责 408 知识讲解，使用 `search_learning_knowledge` 和 [prompts/tutor_prompt.txt](prompts/tutor_prompt.txt)。
- `PlannerAgent`：负责学习计划生成，使用用户画像、学习记录和错题总结工具。
- `MistakeAgent`：负责错题诊断，可以查询/总结/保存错题记录，也可以使用 RAG。
- `ReportAgent`：负责学习周报生成，可以获取当前周、聚合周报输入数据并保存周报。

[agent/react_agent.py](agent/react_agent.py) 是较早的通用 ReAct Agent，目前没有接入 [app.py](app.py)。

### RAG 与向量库

- [rag/rag_service.py](rag/rag_service.py) 从 `VectorStoreService` 检索上下文，填入 [prompts/rag_summarize.txt](prompts/rag_summarize.txt)，再调用共享 chat model。
- [rag/vector_store.py](rag/vector_store.py) 负责 Chroma 初始化、TXT/PDF 加载、文本切分和基于 MD5 的摄入去重。
- [config/chroma.yml](config/chroma.yml) 配置 `collection_name`、`persist_directory`、`k`、`data_path`、允许的文件类型、chunk 大小和重叠长度。
- `VectorStoreService.load_document()` 会修改 Chroma 向量库和 [md5.text](md5.text)。修改 [data/408/](data/408/) 后需要重新运行索引构建命令。
- 大多数项目相对路径通过 `utils.path_tool.get_abs_path()` 解析；但 Chroma 的 `persist_directory` 直接使用配置值，因此实际向量库路径可能受运行命令时的工作目录影响。
- `RagSummarizeService.print_prompt()` 会把最终拼好的 RAG prompt 和上下文打印到 stdout，主要用于调试检索注入是否正确。

### 模型、配置、Prompt 与日志

- [model/factory.py](model/factory.py) 使用 `langchain_openai.ChatOpenAI` 创建共享 `chat_model`，依赖 `MY_API_KEY`、`MY_BASE_URL` 和 [config/rag.yml](config/rag.yml) 中的 `chat_model_name`。
- 共享 Embedding 模型是 `DashScopeEmbeddings`，使用 `embedding_model_name`；DashScope 凭证预期从环境变量读取。
- [utils/config_handler.py](utils/config_handler.py) 在模块导入时加载 YAML 配置，并保存为模块级全局变量。
- [utils/prompt_loader.py](utils/prompt_loader.py) 从 [config/prompts.yml](config/prompts.yml) 读取 prompt 文件路径。
- [utils/logger_handler.py](utils/logger_handler.py) 在导入时创建 [logs/](logs/) 目录，并配置每日 `agent_YYYYMMDD.log` 文件。
- [agent/tools/middleware.py](agent/tools/middleware.py) 负责记录工具调用和模型调用前的日志。

### 本地数据与副作用

这个应用使用本地文件保存演示数据，没有独立数据库：

- [data/study/user_profile.json](data/study/user_profile.json)：演示用户画像。
- [data/study/learning_records.csv](data/study/learning_records.csv)：学习记录。
- [data/study/mistake_records.csv](data/study/mistake_records.csv)：错题记录；`save_mistake_record` 会追加写入。
- [data/study/weekly_reports.json](data/study/weekly_reports.json)：学习周报；`save_weekly_report` 会重写 JSON 文件，且列表型字段按中文分号 `；` 拆分。
- [data/408/](data/408/)：向量库索引的原始知识文件。

运行完整 Agent 流程时要注意副作用：错题和周报工具可能修改 [data/study/](data/study/) 下的数据文件，知识库摄入会修改 Chroma 向量库和 [md5.text](md5.text)。
