# PrimeBuddy 重构任务清单

按顺序做，完成一项勾选一项。括号里是 [`target-architecture.md`](target-architecture.md) 的章节号，细节看那里；每个阶段结束后用评测复测（13）。

## [x] 阶段 0 · 清理旧代码

- **需求描述**：
  - 删掉原项目残留和没有引用的代码，旧系统行为保持不变，不影响之后要测的 v1 基线（16.1）。
- **需要做到**：
  - ✅ 直接在 main 上重构，不另开分支；重构前可演示的旧版本是提交 `228bd9c`；

  - ✅ 按 16.1 删除，`PrimeBuddy.md` 删除；

  - ✅ 16.1 里要注意的两处：`rag/vector_store.py` 的 `__main__` 只删检索"迷路"的几行，保留 `load_document()`（目前唯一的建索引入口）；`main_prompt.txt`、`report_prompt.txt` 留到阶段 1，写人设和周报提示词时参考；

  - ✅ 补写 `CLAUDE.md` 第二部分：运行、测试、建索引的命令和目录说明，之后每个阶段结束时更新；`AGENTS.md` 改成一行 `@CLAUDE.md`，只维护一份；

  - ✅ 四个专家模块能导入，保留的 5 个 prompt 都能读到（命令见下）；`scripts/streamlit_ui_smoke.py` 端到端冒烟通过。旧的单元测试已删除，新测试从阶段 1 起补写。

    ```bash
    uv run python -c "import agent.specialists.tutor_agent, agent.specialists.planner_agent, agent.specialists.mistake_agent, agent.specialists.report_agent; from utils import prompt_loader as p; [f() for f in (p.load_rag_prompts, p.load_tutor_prompts, p.load_planner_prompts, p.load_mistake_prompts, p.load_study_report_prompts)]; print('imports and prompts ok')"
    ```

## [x] 阶段 0 · 锁定依赖并升级 LangChain

- **需求描述**：
  - 用 `pyproject.toml` + `uv.lock` 替换不锁版本的 `requirement.txt`，升级到 langchain 1.5.x（14.1）。
- **需要做到**：
  - 依赖版本可复现，删除 `requirement.txt`，加入 ruff 配置；
  - 升级后，上一项的检查仍全部通过。

## [x] 阶段 0 · 接入 LangSmith 追踪

- **需求描述**：
  - 让旧系统的每次运行都能在 trace 里看到，测基线时方便排查（13.1）。
- **需要做到**：
  - 只配环境变量，不改代码；
  - 4 个演示问题各跑一次，trace 里能看到每次模型调用和工具调用。

## [x] 阶段 0 · 建评测集，跑出 v1 基线

- **需求描述**：
  - 改代码之前先量出旧系统的水平，之后每个阶段用同一套评测对比（13.2–13.4）。
- **需要做到**：
  - 先定下 v2 的主模型，v1 基线也用这个模型跑；
  - 建 `evals/` 骨架和 `targets/v1.py`，数据集有技能选择约 60 条（含审阅时的 8 条口语化问题）、检索约 50 条（标注页码）；
  - 基线报告提交到 `evals/reports/`，包含技能选择准确率、Recall@5、MRR@10、P50 延迟、每次问答的模型调用次数。

## [ ] 阶段 1 · 基础模块：配置、日志、模型、OTel

- **需求描述**：
  - 给新代码用的公共模块，替代 import 时就读配置、建日志文件的旧写法（4.6、13.1、14.2）。
- **需要做到**：
  - `settings.py` 集中读取配置，由一个数据库连接串推导各组件需要的格式；`llm.py` 用 `init_chat_model` 创建 main、small、backup 模型；
  - `observability.py` 初始化 OTel 并接上 FastAPI 埋点，LangChain 埋点的两种方案只开一个；
  - 导入新模块没有副作用；旧的 `utils/`、`model/` 先不删，阶段 2 之前旧 RAG 代码还要用。

## [ ] 阶段 1 · 身份注入与新工具

- **需求描述**：
  - user_id 不再经过模型，工具从运行时上下文读取（5.1、7）。
- **需要做到**：
  - 定义 `Context`，工具通过 `ToolRuntime` 取 user_id，模型可见的参数里没有 `user_id`、`confirm_save`；
  - 工具经 `storage/` 仓储接口访问数据，这一阶段仍读写现有 CSV；
  - 写工具用 `tool_call_id` 做幂等，审批恢复或重放不会重复写入；可预期的失败返回 `{"ok": false, "error": ...}`。

## [ ] 阶段 1 · Skills 技能加载

- **需求描述**：
  - 用按需加载的技能替代关键词路由和 4 个专家类（4.3）。
- **需要做到**：
  - `SkillRegistry` 启动时扫描并校验 `skills/**/SKILL.md`，校验失败直接报错；
  - `load_skill`、`read_skill_file` 可用，读文件时不能越出技能目录；
  - 4 个专家 prompt 迁成 study-408 技能包，全部通过 `skills-ref validate`。

## [ ] 阶段 1 · 主 Agent 与中间件

- **需求描述**：
  - 一个 `create_agent` 主 Agent 加中间件栈承载对话，支持多轮（4.2、5.3、5.4）。
- **需要做到**：
  - `persona.md` 由 `main_prompt.txt` 提炼；每次调用模型前由 `inject_context` 注入人设、技能目录、画像、到期复习和当前时间；
  - 写工具都要经过 `HumanInTheLoopMiddleware` 审批，只读工具失败会重试；每次运行工具调用最多 12 次（其中检索最多 3 次），模型调用最多 15 次；
  - 先用 `InMemorySaver`，同一会话里的追问能接上上一轮。

## [ ] 阶段 1 · 周报工作流

- **需求描述**：
  - 周报改成手写的 LangGraph 工作流：读数据、算数字、校验由代码完成，模型只写文字部分（4.5.1）。
- **需要做到**：
  - 校验不通过（引用了不存在的记录，或下周计划超出可用时长）时打回重写，最多 3 次；当周没有记录时不调用模型；
  - 聊天里用 `generate_weekly_report` 生成，`save_weekly_report(report_id)` 保存原文，审批只有批准和拒绝；
  - `analyze` 节点的提示词参考 `study_report_prompt.txt` 和 `report_prompt.txt`；
  - 单测覆盖校验回路、空数据分支和达到 3 次上限后的输出，补上周范围回退的用例（逻辑沿用现有的 `resolve_report_week`）。

## [ ] 阶段 1 · FastAPI 服务层

- **需求描述**：
  - Agent 通过 API 对外提供服务，支持真流式输出和审批后恢复（3.3、10.1–10.3）。
- **需要做到**：
  - threads、runs（SSE）、resume、feedback 接口可用，事件格式按 10.2；
  - 建 `users`、`threads`、`runs`、`feedback` 表，checkpointer 换成 `AsyncSqliteSaver`，`.gitignore` 加 `data/*.db*`；
  - user_id 只从令牌得出，访问别人的会话会被拒绝；
  - 模型一开始输出，首个 token 就推到前端；trace 里能看到 HTTP 请求、Agent 步骤和工具调用。

## [ ] 阶段 1 · Streamlit 客户端改造

- **需求描述**：
  - `app.py` 改成调用 API 的客户端 `clients/streamlit_app.py`（10.4）。
- **需要做到**：
  - 回答逐 token 显示，去掉 `time.sleep` 模拟打字；
  - 收到审批事件时显示批准、修改、拒绝按钮，周报以卡片展示；
  - 每条回答可以点 👍/👎，有会话列表。

## [ ] 阶段 1 · 集成测试并切换到新内核

- **需求描述**：
  - 用测试和评测确认新内核能替代旧系统，然后删掉旧代码（14.3、16.2）。
- **需要做到**：
  - 集成测试覆盖多轮追问、审批中断与恢复、拒绝后不写入、周报从生成到保存、跨用户访问被拒、关键 span 存在；
  - v2 的技能选择准确率不低于 v1 基线；
  - 删除关键词 Router、4 个专家类、旧入口和已迁移的 prompt 文件（包括阶段 0 保留的两个）。

## [ ] 阶段 2 · 摄入管线与增量索引

- **需求描述**：
  - 重做切片，每个切片带科目、章节和页码；文件更新时自动清理旧切片（8.1、8.2）。
- **需要做到**：
  - 清洗脚本迁到 `rag/ingest/` 并补写测试，先按页拆分再按章节切片，metadata 字段按 8.2；
  - 用 `index()` + `SQLRecordManager` 写入，替代 `md5.text`，建索引入口改为 `scripts/ingest_kb.py`；
  - 先备份 `chroma_db/` 再重建，清掉旧集合和没有集合引用的索引目录；重建后每个切片都有页码。

## [ ] 阶段 2 · 混合检索与新 search_knowledge

- **需求描述**：
  - BM25 + 向量召回，RRF 融合后 rerank；检索工具直接返回切片和出处，不再嵌套调用模型（8.3、8.4）。
- **需要做到**：
  - 按 owner 和科目过滤，owner 条件由代码添加；rerank 不可用时退回融合结果；各阶段都有 OTel span；
  - `search_knowledge` 按 8.4 的格式返回，回答中引用教材内容时带页码；
  - 删除 `RagSummarizeService`、`rag_summarize.txt`、`rag/vector_store.py`，以及旧的 `utils/`、`model/` 和 `config/` 下的旧配置。

## [ ] 阶段 2 · research 子 Agent

- **需求描述**：
  - 多跳检索交给上下文独立的子 Agent，只把结论交回主 Agent（4.4）。
- **需要做到**：
  - 只给只读工具，返回 `ResearchBrief`（答案、要点、引用）；
  - 它内部的 token 不推给前端。

## [ ] 阶段 2 · RAG 评测与消融

- **需求描述**：
  - 用数据说明 RAG 改造的效果（13.2、13.3）。
- **需要做到**：
  - 补齐回答评测集，约 30 条；
  - Recall@5、MRR@10、忠实度、引用正确率、延迟都有 v1/v2 对比；
  - 消融：分别去掉 BM25、去掉 rerank，记录各指标的变化。

## [ ] 阶段 3 · 业务数据迁入数据库

- **需求描述**：
  - 错题、学习记录、周报、复习记录从 CSV/JSON 迁到 SQL 表（9）。
- **需要做到**：
  - 建其余业务表，`scripts/migrate_v1_data.py` 导入现有数据，并为每条错题建复习项；
  - 仓储层切到数据库，工具接口不变；
  - 原 CSV/JSON 移到 `tests/fixtures/` 当种子数据。

## [ ] 阶段 3 · 长期记忆

- **需求描述**：
  - 跨会话记住用户的偏好、约束和目标，用户可以查看和删除（6）。
- **需要做到**：
  - 画像和记忆存进 Store，SQLite 下用 sqlite-vec 做语义检索；
  - 每次运行正常结束后，后台运行记忆整理工作流（`Send` 并行比对候选），新增、更新或删除记忆，旧值归档，敏感信息不入库；
  - 有 `/v1/memories` 接口和记忆页；新开会话仍记得之前说过的约束，用户更正后以新的为准。

## [ ] 阶段 3 · FSRS 复习调度

- **需求描述**：
  - 用 FSRS 安排错题复习，替代"待二刷"这类状态字段（11）。
- **需要做到**：
  - 新增错题时自动建复习项；
  - `get_due_reviews` 能查到期题目，`review_item` 按回忆评分更新下次复习时间，并记复习日志。

## [ ] 阶段 3 · 定时任务与推送

- **需求描述**：
  - 每天推送到期复习，每周日生成周报草稿；无人值守时只跑工作流，不跑 Agent 循环（4.5.2、11）。
- **需要做到**：
  - APScheduler 随 FastAPI 启动，作业存在数据库里，重启不丢；
  - 每日复习推送到飞书或企业微信机器人，同一天不重复推送；
  - 周报草稿以 draft 状态保存，用户在确认页确认后才生效，已确认的周不再生成草稿。

## [ ] 阶段 3 · 反馈回流与评测门禁

- **需求描述**：
  - 把差评、审批被拒和出错的运行变成评测样本，CI 低于阈值时失败（13.5）。
- **需要做到**：
  - `scripts/export_feedback_cases.py` 从自己的数据库还原问题、回答和工具调用，导出候选样本；
  - 用阶段 1 以来积累的反馈做第一轮标注；补上记忆、安全用例和周报首轮校验通过率；
  - `evals/thresholds.yml` 定好每类最低通过数。

## [ ] 阶段 4 · MCP 接入与发布

- **需求描述**：
  - 通过 MCP 使用外部工具，也把 PrimeBuddy 的只读能力开放给其他 MCP 客户端（12）。
- **需要做到**：
  - 用 `langchain.mcp.MCPAdapter` 接一个网页抓取或搜索 server 给 research 用，只加载白名单里的工具，工具描述变化时告警；
  - 用 FastMCP 发布 `search_knowledge`、`get_due_reviews`、`query_mistakes`，HTTP 模式要求 token；
  - 在 Kiro 或其他 MCP 客户端里能查到自己的到期复习。

## [ ] 阶段 4 · 个人知识库技能包

- **需求描述**：
  - 第二个技能包，证明加新领域不用改编排代码（4.3、8.1）。
- **需要做到**：
  - 上传 PDF/Markdown 后按上传者隔离入库，可以带出处问答，`make-flashcards` 生成的闪卡进入复习调度；
  - 改动只涉及技能目录、工具和 API，编排和中间件代码没有改；
  - 补评测：个人资料检索、跨用户隔离、文档注入攻击。

## [ ] 阶段 5 · Docker Compose 部署

- **需求描述**：
  - 部署时换成 Postgres，并验证只改连接串就能切换（9.1、14.4）。
- **需要做到**：
  - compose 里有 api 和带 pgvector 的 Postgres，otel-collector 可选；
  - 改 `PRIMEBUDDY_DATABASE_URL` 后，迁移、摄入和集成测试都通过；
  - 提供 `.env.example`、示例语料和种子数据，王道教材不进仓库。

## [ ] 阶段 5 · CI

- **需求描述**：
  - 每次提交自动检查代码和效果（13.4、14.3）。
- **需要做到**：
  - GitHub Actions 跑 ruff、单元测试和集成测试，集成测试在 SQLite 和 Postgres 上各跑一次；
  - 评测冒烟子集按 `evals/thresholds.yml` 判定，API key 放在 GitHub Secrets。

## [ ] 阶段 5 · README 与简历

- **需求描述**：
  - 整理对外展示的材料（17）。
- **需要做到**：
  - README 包含定位、架构图、v1/v2 指标表、演示 GIF，以及本地和 Docker 两种快速开始；
  - `CLAUDE.md` 第二部分按新架构重写；
  - 简历里的每个数字都能在 `evals/reports/` 找到对应报告。
