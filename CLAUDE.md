# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) and other coding agents when working with code in this repository.

---

# 第一部分：通用智能体行为准则

用于减少大语言模型常见编码错误的行为准则。根据需要与项目特定说明结合使用。  
**权衡：** 这些准则更偏重谨慎而非速度。对于简单任务，请自行判断。

## 1. 编码前先思考
**不要想当然。不要掩盖困惑。明确说明取舍。**  
实施前：
- 明确说明你的假设。如果不确定，请先询问。
- 如果存在多种理解，请全部说明，不要自行默默选择。
- 如果存在更简单的方案，请明确指出。必要时提出异议。
- 如果有不清楚之处，请停下来，指出困惑所在并询问。

## 2. 简单优先
**用最少的代码解决问题。不做推测性设计。**
- 不添加要求之外的功能。
- 不为只使用一次的代码创建抽象。
- 不增加未被要求的“灵活性”或“可配置性”。
- 不为不可能发生的场景添加错误处理。
- 如果写了 200 行代码，而 50 行就能解决，请重写。  
问问自己：“资深工程师会不会认为这过于复杂？”如果会，请简化。

## 3. 精准改动
**只改必须改的内容。只清理自己产生的问题。**  
编辑现有代码时：
- 不要顺手“改进”相邻代码、注释或格式。
- 不要重构没有问题的代码。
- 遵循现有风格，即使你会采用不同的写法。
- 如果发现无关的无效代码，请指出，但不要删除。  
当你的改动产生遗留内容时：
- 删除因你的改动而不再使用的导入、变量和函数。
- 除非明确要求，否则不要删除原本就存在的无效代码。  
判断标准：每一处改动都应能直接追溯到用户的要求。

## 4. 目标驱动执行
**定义成功标准。循环执行，直到验证通过。**  
将任务转化为可验证的目标：
- “添加校验” → “为无效输入编写测试，然后让测试通过”
- “修复缺陷” → “编写能够复现缺陷的测试，然后让测试通过”
- “重构 X” → “确保重构前后测试均能通过”  
对于多步骤任务，给出简短计划：
```
1. [步骤] → 验证：[检查方式]
2. [步骤] → 验证：[检查方式]
3. [步骤] → 验证：[检查方式]
```
明确的成功标准能让你独立循环执行。模糊的标准（如“让它能用”）则需要不断澄清。

---
**这些准则有效的表现：** 差异中不必要的改动更少，因过度复杂而返工的情况更少，并且澄清问题发生在实施之前，而不是出错之后。

## 5. 完成标准
交付前确认：
- 实现满足当前需求，没有附带无关功能或重构。
- 目录归属、扩展权限与持久化数据兼容性未被意外破坏。
- 相关测试与检查已经通过，或未验证项已明确说明。
- 差异中没有生成产物、调试代码、临时文件或敏感信息。
- 最终说明简要列出改动内容、验证结果和必要的后续操作。

## 6. 重要约定
- **Git 提交**
  - 仅在用户明确要求时创建提交。
  - 格式：使用 `<type>: <中文描述>`。
  - 允许的类型：`feat`、`fix`、`refactor`、`chore`、`docs`、`test`、`perf`、`build`、`ci`、`style`、`revert`。
  - 每个提交应只包含一项独立且完整的变更。
  - 提交说明和 PR 描述中不要添加 `Co-Authored-By` 等 AI 署名行或生成工具的署名。
- **代码注释**
  - 改动代码时，代码注释要和附近的代码（或者同类代码）的语言、语气与密度保持一致。

---

# 第二部分：PrimeBuddy项目架构与开发指南

## 1. 当前状态
- PrimeBuddy 是面向 408 考研的 Streamlit + LangChain 多 Agent RAG 应用，正在重构为通用个人 Agent。
- 重构直接在 `main` 上进行，不另开分支。重构前可演示的旧版本是提交 `228bd9c`。
- 目标设计见 `docs/target-architecture.md`，任务顺序见 `docs/todo.md`。动手前先读对应章节；新代码按设计第 15 节放进 `src/primebuddy/`。
- 旧模块按设计 16.2 的时机删除，不要提前删：`utils/`、`model/`、`config/*.yml` 到阶段 2 才删（旧 RAG 依赖它们）；`prompts/main_prompt.txt`、`prompts/report_prompt.txt` 已不被加载，保留给阶段 1 参考。

## 2. 环境
- conda 环境 `agent`（Python 3.11），命令统一用 `conda run -n agent <command>`；依赖用 `pip install -r requirement.txt` 安装（阶段 0 会改为 `pyproject.toml` + uv）。
- 环境变量：`MY_API_KEY`、`MY_BASE_URL`（OpenAI 兼容接口），`DASHSCOPE_API_KEY`（Embedding）。聊天模型名只从 `config/rag.yml` 的 `chat_model_name` 读取，环境变量 `MY_MODEL` 不生效。
- 环境变量写在用户的 `~/.zshrc` 里，Agent 的终端可能还是旧值。需要调用模型时用 `zsh -lic '<command>'` 加载；不要打印 key 的值。

## 3. 常用命令
```bash
# 启动应用
conda run -n agent streamlit run app.py

# 修改 data/408 后增量建索引（按文件 MD5 去重，记录在 md5.text）
conda run -n agent python rag/vector_store.py

# 导入与 prompt 检查：四个专家模块能导入、5 个 prompt 能读取，不需要模型 key
conda run -n agent python -c "import agent.specialists.tutor_agent, agent.specialists.planner_agent, agent.specialists.mistake_agent, agent.specialists.report_agent; from utils import prompt_loader as p; [f() for f in (p.load_rag_prompts, p.load_tutor_prompts, p.load_planner_prompts, p.load_mistake_prompts, p.load_study_report_prompts)]; print('imports and prompts ok')"

# 端到端冒烟：用真实模型跑 4 个演示问题（约 3 分钟），并检查没有写入错题和周报数据
conda run -n agent python scripts/streamlit_ui_smoke.py
```
- 目前没有单元测试：旧测试已删除，新测试从阶段 1 起按设计 14.3 补写。在此之前，改动后至少跑导入与 prompt 检查；涉及模型调用、工具或 RAG 的改动再跑端到端冒烟。

## 4. 代码结构（旧系统）
- 调用链：`app.py` → `agent/study_supervisor.py`（关键词路由，专家按需创建）→ `agent/specialists/`（4 个专家，`create_agent` + `agent/tools/middleware.py`）→ `agent/tools/`（检索、学习记录、错题、周报工具）。
- `rag/rag_service.py` 检索后再调用一次模型做总结；`rag/vector_store.py` 管理 Chroma（集合 `primebuddy_408`，目录 `chroma_db/`）。
- `agent/tools/study_tools.get_rag_service()` 加锁保证只创建一个 Chroma 客户端。模型会并行调用检索工具，去掉锁会导致并发初始化报错。
- `model/factory.py` 创建聊天模型和 Embedding；`utils/` 负责路径、配置（import 时加载 YAML）、日志（import 时创建 `logs/`）和 prompt 加载。
- `scripts/clean_wangdao_os_ocr.py` 清洗 OCR 文本。

## 5. 数据与副作用
- `data/study/` 存放画像、学习记录、错题（CSV）和周报（JSON）。`save_mistake_record`、`save_weekly_report` 只有在 `confirm_save=True` 时才写入；跑完整流程后用 `git status` 确认这些文件没有被意外改动。
- 不进仓库：`data/408/*.txt`、`data/raw/`（教材，有版权）、`chroma_db/`、`md5*.text`、`logs/`。

## 6. 注意事项
- 以下文件用 CRLF 换行，修改时保持：`config/rag.yml`、`data/study/weekly_reports.json`、`model/factory.py`、`prompts/rag_summarize.txt`、`rag/vector_store.py`、`utils/config_handler.py`、`utils/file_handler.py`、`utils/logger_handler.py`、`utils/path_tool.py`。
- 项目内路径用 `utils.path_tool.get_abs_path()` 解析，不依赖当前工作目录。
