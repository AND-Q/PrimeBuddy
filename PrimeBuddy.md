# PrimeBuddy 项目完整文档

## 目录

1. [项目总览](#1-项目总览)
2. [项目背景与改造目标](#2-项目背景与改造目标)
3. [项目定位与核心价值](#3-项目定位与核心价值)
4. [核心功能说明](#4-核心功能说明)
5. [整体系统架构](#5-整体系统架构)
6. [用户请求完整执行链路](#6-用户请求完整执行链路)
7. [Supervisor 路由机制](#7-supervisor-路由机制)
8. [四个专家 Agent 设计](#8-四个专家-agent-设计)
9. [工具系统设计](#9-工具系统设计)
10. [RAG 知识库设计](#10-rag-知识库设计)
11. [数据设计](#11-数据设计)
12. [Prompt 设计](#12-prompt-设计)
13. [配置系统](#13-配置系统)
14. [项目目录结构](#14-项目目录结构)
15. [核心文件逐个说明](#15-核心文件逐个说明)
16. [运行方式](#16-运行方式)
17. [演示问题与预期效果](#17-演示问题与预期效果)
18. [验证方式](#18-验证方式)
19. [日志与调试](#19-日志与调试)
20. [当前阶段边界与局限](#20-当前阶段边界与局限)
21. [项目亮点](#21-项目亮点)
22. [面试讲解指南](#22-面试讲解指南)
23. [面试官可能追问与回答方向](#23-面试官可能追问与回答方向)
24. [后续扩展路线](#24-后续扩展路线)
25. [总结](#25-总结)

---

## 1. 项目总览

**PrimeBuddy** 是一个面向学习规划与诊断的多 Agent 智能学习伙伴项目。

当前第一阶段以 **408 考研学习** 作为落地场景，围绕计算机考研 408 的四门核心科目：

- 数据结构
- 计算机组成原理
- 操作系统
- 计算机网络

实现一个能够完成以下学习闭环的智能系统：

```text
知识问答 -> 错题分析 -> 薄弱点识别 -> 学习计划 -> 学习周报 -> 下周调整
```

从用户视角看，PrimeBuddy 是一个 Streamlit 聊天应用。用户可以直接输入学习问题、计划需求、错题描述或周报请求，系统会返回结构化回答。

从技术视角看，PrimeBuddy 是一个基于 **LangChain Agent + 轻量 Supervisor + RAG + CSV/JSON 学习数据** 的多 Agent 学习助手。它不是把所有能力塞进一个大 Prompt，而是将学习任务拆分给多个专家 Agent：

| 角色 | 职责 |
| --- | --- |
| Supervisor | 判断用户意图，将问题路由给合适专家 Agent |
| Tutor Agent | 负责 408 知识问答和考点讲解 |
| Planner Agent | 负责学习计划生成 |
| Mistake Agent | 负责错题分析和错因诊断 |
| Report Agent | 负责学习周报生成 |

当前项目的主要入口是：

```text
app.py
```

主控逻辑位于：

```text
agent/study_supervisor.py
```

---

## 2. 项目背景与改造目标

### 2.1 项目原始基础

本项目最初是一个基础 LangChain / Streamlit / RAG demo，已经具备以下基础能力：

- Streamlit 聊天界面
- LangChain Agent 创建
- 工具调用机制
- 中间件日志记录
- Prompt 文件加载
- Chroma 向量数据库
- 文档加载与切分
- CSV 外部数据读取
- YAML 配置管理

这些能力本身适合作为大模型应用开发的基础框架，但原始场景偏向简单客服 demo，业务深度和面试展示价值有限。

### 2.2 改造目标

PrimeBuddy 的改造目标是：

1. **从普通问答 demo 升级为完整学习 Agent 项目**
   - 不只回答问题，还能分析学习状态、制定计划、总结周报。

2. **形成可讲清楚的多 Agent 架构**
   - 使用 Supervisor 负责路由，专家 Agent 分工处理不同学习任务。

3. **保留已有工程基础并进行场景升级**
   - 复用 Streamlit、LangChain、Chroma、YAML 配置、Prompt Loader、日志系统。

4. **以 408 考研作为第一阶段落地场景**
   - 数据明确，演示问题清晰，适合面试展示。

5. **保留未来扩展空间**
   - 项目名不绑定 408。
   - 后续可扩展到课程学习、考试分析、择校建议、复试模拟等场景。

### 2.3 为什么叫 PrimeBuddy

**PrimeBuddy** 可以理解为：

- **Prime**：核心、优选、进阶、旗舰。
- **Buddy**：伙伴、陪伴式助手。

这个名字强调它不是一个只服务 408 的工具，而是一个可以扩展为通用学习伙伴的平台。

当前阶段的完整定位可以概括为：

```text
PrimeBuddy 是一个面向学习规划与诊断的多 Agent 智能学习伙伴。
它会先理解用户意图，再检索学习资料或读取学习记录，最后给出结构化学习建议。
当前第一阶段以 408 考研学习为演示场景。
```

---

## 3. 项目定位与核心价值

### 3.1 项目不是普通聊天机器人

普通聊天机器人通常只做一件事：根据用户输入直接生成回答。

PrimeBuddy 的目标不是简单问答，而是构建学习闭环：

```text
知识讲解
  ↓
错题诊断
  ↓
薄弱点总结
  ↓
学习计划
  ↓
周报复盘
  ↓
下一阶段调整
```

这使项目更像一个学习管理与诊断系统，而不是一个单纯的聊天 UI。

### 3.2 项目不是一个大 Prompt

如果把所有能力都写在一个 Prompt 中，系统会出现几个问题：

- Prompt 越来越长，难以维护。
- 不同任务之间规则混杂。
- 工具过多，Agent 可能误调用。
- 面试时很难讲出清晰架构。

PrimeBuddy 使用多 Agent 分工：

- Tutor 专心讲知识。
- Planner 专心制定计划。
- Mistake 专心分析错题。
- Report 专心生成周报。

这样每个 Agent 的职责更清晰，工具集合更小，输出风格也更稳定。

### 3.3 项目适合面试展示

PrimeBuddy 适合作为实习面试项目，原因包括：

1. **技术栈完整**
   - Streamlit、LangChain、Agent、Tool、RAG、Chroma、Prompt、配置管理、日志系统。

2. **业务闭环清晰**
   - 从知识问答到计划、错题、周报，能体现产品思维。

3. **架构容易讲解**
   - Supervisor + 多专家 Agent 的结构层次明确。

4. **可扩展性强**
   - 未来可以迁移 LangGraph、接数据库、加 Exam Agent、School Agent。

5. **演示稳定**
   - 第一阶段使用确定性关键词路由，而不是完全依赖 LLM 分类。

---

## 4. 核心功能说明

PrimeBuddy 当前第一阶段包含四个核心功能。

### 4.1 408 知识问答

用户可以询问 408 相关知识点，例如：

```text
请用 408 考研的角度讲一下操作系统中的虚拟内存，并说明常见考点。
```

系统会路由到 Tutor Agent。

Tutor Agent 会调用学习知识库检索工具，从 `data/408` 中召回相关资料，再结合 RAG Prompt 生成回答。

典型输出包括：

- 直接解释
- 核心概念
- 408 常见考法
- 易错点
- 例子或练习建议

### 4.2 学习计划生成

用户可以提出计划需求，例如：

```text
我还有 8 周考 408，每天能学 3 小时，操作系统和计网比较弱，帮我制定下周计划。
```

系统会路由到 Planner Agent。

Planner Agent 会结合：

- 用户画像
- 学习记录
- 错题摘要
- 用户输入的目标和时间约束

生成结构化学习计划。

典型输出包括：

- 当前阶段判断
- 本周目标
- 每日任务安排
- 时间分配建议
- 复盘节奏
- 风险提醒
- 调整建议

### 4.3 错题分析

用户可以描述一道错题，例如：

```text
我做错了一道题：TCP 拥塞控制中慢开始和拥塞避免的区别是什么？我把阈值变化理解错了，帮我分析原因并给复习建议。
```

系统会路由到 Mistake Agent。

Mistake Agent 可以：

- 查询已有错题记录
- 总结错题分布
- 调用知识库检索相关知识
- 分析错因
- 给出复习动作
- 在需要时保存新的错题记录

典型输出包括：

- 涉及知识点
- 错因分析
- 正确推理路径
- 相似陷阱
- 复习动作
- 是否建议保存到错题记录

### 4.4 学习周报生成

用户可以请求学习周报，例如：

```text
请生成我的本周学习报告，指出主要问题和下周重点。
```

系统会路由到 Report Agent。

Report Agent 会聚合：

- 当前自然周范围
- 用户画像
- 本周学习记录
- 本周错题记录
- 学习统计摘要
- 错题统计摘要

然后生成周报。

典型输出包括：

- 本周学习概览
- 各科投入情况
- 任务完成情况
- 高频错题与薄弱点
- 进度评价
- 下周优先级
- 风险提醒

---

## 5. 整体系统架构

PrimeBuddy 当前采用轻量 Supervisor 架构。

整体架构如下：

```text
用户
  ↓
Streamlit 聊天界面 app.py
  ↓
StudyCopilotSupervisor
  ↓
意图路由 route(query)
  ↓
┌──────────────────────────────────────────────┐
│                                              │
│  Tutor Agent     Planner Agent               │
│  知识问答        学习计划                    │
│                                              │
│  Mistake Agent   Report Agent                │
│  错题分析        学习周报                    │
│                                              │
└──────────────────────────────────────────────┘
  ↓
工具调用层
  ↓
┌──────────────────────────────────────────────┐
│ RAG 检索工具                                 │
│ 用户画像工具                                 │
│ 学习记录工具                                 │
│ 错题查询/摘要/保存工具                       │
│ 周报输入聚合/保存工具                        │
└──────────────────────────────────────────────┘
  ↓
数据与知识库层
  ↓
┌──────────────────────────────────────────────┐
│ data/408 408 知识资料                         │
│ data/study 用户画像、学习记录、错题、周报      │
│ Chroma 向量库                                 │
└──────────────────────────────────────────────┘
```

### 5.1 分层说明

| 层级 | 文件/目录 | 职责 |
| --- | --- | --- |
| 前端层 | `app.py` | 提供 Streamlit 聊天界面 |
| 路由层 | `agent/study_supervisor.py` | 判断用户意图并分发任务 |
| 专家 Agent 层 | `agent/specialists/` | 执行具体学习任务 |
| 工具层 | `agent/tools/` | 提供 RAG、记录读取、错题保存、周报聚合等能力 |
| RAG 层 | `rag/` | 构建向量库、检索资料、总结回答 |
| 模型层 | `model/factory.py` | 创建 Chat Model 和 Embedding Model |
| 数据层 | `data/` | 保存 408 知识文件和学习记录 |
| 配置层 | `config/` | 保存模型、向量库、Prompt、数据路径配置 |
| 基础设施层 | `utils/` | 路径、日志、文件加载、配置加载、Prompt 加载 |

### 5.2 为什么第一阶段不用 LangGraph

第一阶段没有直接使用 LangGraph 图编排，而是采用普通 Python 类实现轻量 Supervisor。

原因是：

1. 当前阶段优先保证演示稳定。
2. 四个专家 Agent 的职责比较独立，不需要复杂状态图。
3. 确定性关键词路由更容易调试。
4. 轻量 Supervisor 更适合快速面试展示。
5. 后续可以在 Phase 1.5 迁移到 LangGraph。

面试时可以这样解释：

```text
我第一阶段没有一开始就上 LangGraph，而是先用轻量 Supervisor 把路由和专家 Agent 接口稳定下来。
这样可以先保证 demo 可运行、功能闭环清晰。等专家 Agent 的输入输出稳定后，再把 Supervisor 迁移成 LangGraph 中的节点和边。
```

---

## 6. 用户请求完整执行链路

以用户在页面输入一句话为例，完整流程如下：

```text
用户输入问题
  ↓
Streamlit st.chat_input 接收输入
  ↓
写入 st.session_state["message"]
  ↓
调用 st.session_state["agent"].execute_stream(prompt)
  ↓
StudyCopilotSupervisor.route(query) 判断路由
  ↓
根据路由选择专家 Agent
  ↓
专家 Agent 使用 LangChain create_agent 执行
  ↓
必要时调用工具
  ↓
工具读取知识库或学习数据
  ↓
模型生成回答
  ↓
execute_stream 按 chunk 返回
  ↓
Streamlit write_stream 流式展示
  ↓
完整回答写入聊天历史
```

当前 `app.py` 中已经修复了流式响应保存问题。

旧问题是：如果只保存最后一个流式 chunk，聊天历史会丢失完整回答。

当前做法是：

```python
response_messages = []

for chunk in generator:
    response_messages.append(chunk)

st.session_state["message"].append({
    "role": "assistant",
    "content": "".join(response_messages).strip()
})
```

这样可以保证页面 rerun 后仍然显示完整回答。

---

## 7. Supervisor 路由机制

Supervisor 位于：

```text
agent/study_supervisor.py
```

核心类是：

```python
StudyCopilotSupervisor
```

### 7.1 Supervisor 的职责

Supervisor 的职责不是直接回答用户问题，而是：

1. 接收用户输入。
2. 判断输入属于哪类学习任务。
3. 路由给对应专家 Agent。
4. 记录路由日志。
5. 对无法分类的问题返回能力说明。

### 7.2 路由结果对象

代码中定义了一个 `RouteResult`：

```python
@dataclass
class RouteResult:
    route: str
    reason: str
```

其中：

- `route` 表示路由类型。
- `reason` 表示路由原因，方便日志和调试。

### 7.3 当前支持的路由

| route | 对应 Agent | 典型问题 |
| --- | --- | --- |
| `tutor` | Tutor Agent | 讲一下虚拟内存、解释 TCP、区别进程和线程 |
| `planner` | Planner Agent | 制定计划、安排复习、每天学多久 |
| `mistake` | Mistake Agent | 我做错了、错因分析、为什么错 |
| `report` | Report Agent | 周报、本周总结、学习报告、下周重点 |
| `general` | 无专家 Agent | 能力介绍或无法分类的问题 |

### 7.4 路由优先级

当前路由优先级是：

```text
report > mistake > planner > tutor > general
```

这样设计的原因是：

- “复盘”“总结”等词可能既像计划，也像报告，所以报告优先。
- “错题复盘”可能同时命中错题和复盘，所以错题优先于计划和问答。
- “复习计划”可能包含知识点词汇，所以计划优先于问答。

### 7.5 当前关键词示例

```python
report_keywords = ["周报", "学习报告", "本周", "这周", "总结", "复盘", "下周重点", "阶段报告"]
mistake_keywords = ["错题", "错了", "做错", "选错", "正确答案", "错因", "为什么错", "不会做", "二刷"]
planner_keywords = ["计划", "安排", "规划", "复习", "每天", "每周", "还有", "目标分", "冲刺", "进度"]
tutor_keywords = ["讲一下", "解释", "是什么", "区别", "考法", "知识点", "例题", "概念", "原理", "流程"]
```

### 7.6 为什么使用关键词路由

第一阶段选择关键词路由，是为了稳定。

优点：

- 可控。
- 可解释。
- 方便调试。
- 面试演示时不容易出现 LLM 分类漂移。

缺点：

- 对表达方式比较依赖关键词。
- 复杂意图可能需要更多规则。
- 后续如果任务类型变多，需要维护关键词表。

未来可以升级为：

```text
规则路由 + LLM 分类器 + 置信度 + 追问机制
```

---

## 8. 四个专家 Agent 设计

四个专家 Agent 位于：

```text
agent/specialists/
```

目录包括：

```text
agent/specialists/tutor_agent.py
agent/specialists/planner_agent.py
agent/specialists/mistake_agent.py
agent/specialists/report_agent.py
```

四个 Agent 都采用统一接口：

```python
def execute(self, query: str) -> str

def execute_stream(self, query: str)
```

这样 Supervisor 不需要关心每个专家内部细节，只需要把用户问题转发进去。

### 8.1 Tutor Agent

文件：

```text
agent/specialists/tutor_agent.py
```

职责：

- 解答 408 知识点。
- 从学习知识库检索资料。
- 输出考试导向解释。
- 总结常见考法和易错点。

注册工具：

```python
search_learning_knowledge
```

Prompt Loader：

```python
load_tutor_prompts()
```

适合处理的问题：

```text
请讲一下操作系统中的虚拟内存。
TCP 慢开始和拥塞避免有什么区别？
Dijkstra 算法为什么不能处理负权边？
Cache 直接映射和组相联映射有什么区别？
```

典型输出结构：

1. 直接回答。
2. 核心概念。
3. 408 常见考法。
4. 易错点。
5. 小例子或练习建议。

### 8.2 Planner Agent

文件：

```text
agent/specialists/planner_agent.py
```

职责：

- 根据目标、时间、薄弱科目生成计划。
- 结合用户画像、学习记录和错题摘要。
- 输出可执行的周计划或日计划。

注册工具：

```python
get_user_profile
get_learning_records
summarize_mistakes
```

Prompt Loader：

```python
load_planner_prompts()
```

适合处理的问题：

```text
我还有 8 周考 408，每天能学 3 小时，帮我制定下周计划。
我操作系统和计网比较弱，应该怎么安排复习？
我目标 120 分，现在基础一般，怎么规划强化阶段？
```

典型输出结构：

1. 当前阶段判断。
2. 本周目标。
3. 每日任务安排。
4. 时间分配。
5. 复盘节奏。
6. 风险提醒。
7. 动态调整建议。

### 8.3 Mistake Agent

文件：

```text
agent/specialists/mistake_agent.py
```

职责：

- 分析错题。
- 判断知识点。
- 总结错因。
- 给出复习动作。
- 必要时保存错题记录。

注册工具：

```python
query_mistake_records
summarize_mistakes
save_mistake_record
search_learning_knowledge
```

Prompt Loader：

```python
load_mistake_prompts()
```

适合处理的问题：

```text
我做错了一道 TCP 拥塞控制题，帮我分析原因。
这道 Dijkstra 题为什么不能选 A？
我总是把页和页框混淆，应该怎么复习？
```

典型输出结构：

1. 涉及知识点。
2. 错因分析。
3. 正确推理路径。
4. 相似陷阱。
5. 复习动作。
6. 是否建议保存到错题记录。

### 8.4 Report Agent

文件：

```text
agent/specialists/report_agent.py
```

职责：

- 生成学习周报。
- 聚合学习记录和错题记录。
- 总结薄弱点和下周重点。
- 必要时保存周报。

注册工具：

```python
get_current_week_range
get_weekly_report_inputs
save_weekly_report
```

Prompt Loader：

```python
load_study_report_prompts()
```

适合处理的问题：

```text
请生成我的本周学习报告。
总结一下我这周 408 的主要问题。
下周我应该重点复习什么？
```

典型输出结构：

1. 本周学习概览。
2. 各科投入分布。
3. 任务完成情况。
4. 高频错题与薄弱点。
5. 进度评价。
6. 下周优先级。
7. 风险提醒。

---

## 9. 工具系统设计

工具位于：

```text
agent/tools/
```

当前工具保持了原项目中比较直接的 LangChain Tool 写法：

```python
from langchain_core.tools import tool

@tool(description="...")
def some_tool(...):
    ...
```

这样写的好处是：

- 简单直观。
- 方便 LangChain Agent 注册。
- 适合小型 demo 和面试展示。
- 工具职责清晰，方便单独测试。

### 9.1 study_tools.py

文件：

```text
agent/tools/study_tools.py
```

核心工具：

```python
search_learning_knowledge(query: str) -> str
```

职责：

- 封装 `RagSummarizeService`。
- 从 PrimeBuddy 学习知识库中检索资料。
- 第一阶段知识库聚焦 408 考研内容。

使用场景：

- Tutor Agent 解答知识点。
- Mistake Agent 分析错题时检索相关知识。

### 9.2 record_tools.py

文件：

```text
agent/tools/record_tools.py
```

核心工具：

```python
get_user_profile(user_id: str) -> str
get_learning_records(user_id: str, start_date: str = "", end_date: str = "") -> str
```

职责：

- 读取用户画像。
- 按日期范围读取学习记录。
- 将结果序列化为 JSON 字符串返回给 Agent。

内部数据文件：

```text
data/study/user_profile.json
data/study/learning_records.csv
```

### 9.3 mistake_tools.py

文件：

```text
agent/tools/mistake_tools.py
```

核心工具：

```python
query_mistake_records(...)
summarize_mistakes(...)
save_mistake_record(...)
```

职责：

- 查询错题记录。
- 汇总错题数量、科目分布、知识点分布、错因分布。
- 追加保存新错题。

内部数据文件：

```text
data/study/mistake_records.csv
```

错题 ID 格式：

```text
M001, M002, M003, ...
```

保存新错题时，会自动生成下一个 ID。

### 9.4 report_tools.py

文件：

```text
agent/tools/report_tools.py
```

核心工具：

```python
get_current_week_range() -> str
get_weekly_report_inputs(user_id: str, week_start: str, week_end: str) -> str
save_weekly_report(...)
```

职责：

- 获取当前自然周起止日期。
- 聚合周报输入数据。
- 保存学习周报。

内部数据文件：

```text
data/study/weekly_reports.json
```

周报输入包括：

- 用户画像。
- 周起止日期。
- 学习记录摘要。
- 错题记录摘要。
- 原始学习记录。
- 原始错题记录。

### 9.5 middleware.py

文件：

```text
agent/tools/middleware.py
```

当前中间件主要包括：

```python
monitor_tool
log_before_model
```

职责：

- 记录工具调用名称。
- 记录工具调用参数。
- 记录工具调用成功或失败。
- 在模型调用前记录消息数量和最后一条消息内容。

当前已经移除了旧项目中的动态报告 Prompt 切换逻辑，因为 PrimeBuddy 中每个专家 Agent 都拥有自己的独立 Prompt，不再需要运行时切换身份。

---

## 10. RAG 知识库设计

RAG 相关代码位于：

```text
rag/
```

包括：

```text
rag/rag_service.py
rag/vector_store.py
```

### 10.1 RAG 的作用

RAG 的全称是 Retrieval-Augmented Generation，即检索增强生成。

在 PrimeBuddy 中，RAG 的作用是：

1. 先从本地 408 知识库中检索相关资料。
2. 再把资料和用户问题一起交给模型。
3. 让模型基于资料生成更可靠的回答。

这样可以减少模型凭空编造，也能让回答更贴合当前项目准备的 408 演示知识库。

### 10.2 知识库文件

当前 408 知识库位于：

```text
data/408/
```

包含：

```text
data/408/data_structure.txt
data/408/computer_organization.txt
data/408/operating_system.txt
data/408/computer_network.txt
```

对应四门科目：

| 文件 | 科目 |
| --- | --- |
| `data_structure.txt` | 数据结构 |
| `computer_organization.txt` | 计算机组成原理 |
| `operating_system.txt` | 操作系统 |
| `computer_network.txt` | 计算机网络 |

### 10.3 向量库服务

文件：

```text
rag/vector_store.py
```

核心类：

```python
VectorStoreService
```

职责：

- 初始化 Chroma 向量库。
- 初始化文本切分器。
- 扫描知识文件。
- 计算文件 MD5。
- 跳过已加载文件。
- 加载 TXT/PDF 文档。
- 将文档切分为小块。
- 写入 Chroma。
- 提供 Retriever 给 RAG 使用。

### 10.4 文本切分配置

当前配置位于：

```text
config/chroma.yml
```

内容包括：

```yaml
collection_name: primebuddy_408
persist_directory: chroma_db
k: 3
data_path: data/408
md5_hex_store: md5.text
allow_knowledge_file_type: ["txt", "pdf"]

chunk_size: 200
chunk_overlap: 20
separators: ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
```

含义：

| 配置项 | 含义 |
| --- | --- |
| `collection_name` | Chroma 集合名称 |
| `persist_directory` | 向量库持久化目录 |
| `k` | 每次检索返回文档数量 |
| `data_path` | 知识文件目录 |
| `md5_hex_store` | 已加载文件的 MD5 记录 |
| `allow_knowledge_file_type` | 支持加载的文件类型 |
| `chunk_size` | 文本块最大长度 |
| `chunk_overlap` | 相邻文本块重叠长度 |
| `separators` | 文本切分分隔符 |

### 10.5 RAG 总结服务

文件：

```text
rag/rag_service.py
```

核心类：

```python
RagSummarizeService
```

核心流程：

```text
用户问题
  ↓
retriever.invoke(query)
  ↓
召回相关文档
  ↓
拼接参考资料 context
  ↓
加载 rag_summarize Prompt
  ↓
PromptTemplate 格式化
  ↓
Chat Model 生成回答
  ↓
StrOutputParser 输出文本
```

### 10.6 RAG 工具和 Agent 的关系

RAG 本身不是直接面对用户的 Agent。

它通过工具暴露给 Agent：

```text
search_learning_knowledge
```

然后由 Tutor Agent 或 Mistake Agent 在需要时调用。

---

## 11. 数据设计

PrimeBuddy 第一阶段使用 CSV/JSON 作为演示数据层。

原因：

1. 数据结构直观，面试官可以直接打开看。
2. 不需要额外数据库部署。
3. 适合 Streamlit demo。
4. 后续可以平滑迁移到 SQLite 或其他数据库。

数据主要位于：

```text
data/study/
```

### 11.1 用户画像 user_profile.json

文件：

```text
data/study/user_profile.json
```

示例字段：

```json
{
  "user_id": "demo_user",
  "name": "PrimeBuddy Demo Learner",
  "exam": "408 考研",
  "exam_date": "2026-12-20",
  "target_score": 120,
  "current_estimated_score": 85,
  "daily_available_hours": 3,
  "current_stage": "强化阶段",
  "weak_subjects": ["操作系统", "计算机网络"],
  "preferred_style": "计划清晰、任务可执行、每周复盘"
}
```

用途：

- Planner Agent 制定计划。
- Report Agent 生成周报。
- 后续可扩展为多用户画像。

### 11.2 学习记录 learning_records.csv

文件：

```text
data/study/learning_records.csv
```

字段：

| 字段 | 含义 |
| --- | --- |
| `date` | 学习日期 |
| `user_id` | 用户 ID |
| `subject` | 科目 |
| `chapter` | 章节或知识点 |
| `duration_minutes` | 学习时长，单位分钟 |
| `task_type` | 任务类型 |
| `completed` | 是否完成 |
| `notes` | 备注 |

用途：

- Planner Agent 根据近期记录调整计划。
- Report Agent 统计本周学习投入。

### 11.3 错题记录 mistake_records.csv

文件：

```text
data/study/mistake_records.csv
```

字段：

| 字段 | 含义 |
| --- | --- |
| `id` | 错题 ID |
| `date` | 错题日期 |
| `user_id` | 用户 ID |
| `subject` | 科目 |
| `chapter` | 章节 |
| `question` | 题目描述 |
| `user_answer` | 用户答案 |
| `correct_answer` | 正确答案 |
| `error_reason` | 错因 |
| `knowledge_point` | 知识点 |
| `status` | 复习状态 |

用途：

- Mistake Agent 查询和保存错题。
- Planner Agent 识别薄弱点。
- Report Agent 汇总错题模式。

### 11.4 周报记录 weekly_reports.json

文件：

```text
data/study/weekly_reports.json
```

字段包括：

- `user_id`
- `week_start`
- `week_end`
- `summary`
- `strengths`
- `weaknesses`
- `recommended_next_week_plan`
- `risk_flags`

用途：

- 保存历史周报。
- 后续可以扩展为阶段报告或趋势分析。

### 11.5 data/external/records.csv

项目中仍保留：

```text
data/external/records.csv
```

当前已经替换为学习记录兼容数据，用于保留原有配置结构。

PrimeBuddy 第一阶段主流程主要使用 `data/study` 下的数据。

---

## 12. Prompt 设计

Prompt 文件位于：

```text
prompts/
```

当前包括：

```text
prompts/main_prompt.txt
prompts/rag_summarize.txt
prompts/report_prompt.txt
prompts/supervisor_prompt.txt
prompts/tutor_prompt.txt
prompts/planner_prompt.txt
prompts/mistake_prompt.txt
prompts/study_report_prompt.txt
```

### 12.1 为什么需要多个 Prompt

不同学习任务的目标不同。

如果用一个 Prompt 处理所有任务，会导致：

- 知识问答和计划生成风格混杂。
- 错题分析不够聚焦。
- 周报输出结构不稳定。
- 工具使用边界不清晰。

所以 PrimeBuddy 将 Prompt 按 Agent 拆分。

### 12.2 main_prompt.txt

用途：

- 保留给兼容性的 ReactAgent 使用。
- 描述 PrimeBuddy 的整体学习助手身份。

当前主入口 `app.py` 使用的是 `StudyCopilotSupervisor`，不是旧的 `ReactAgent`。

### 12.3 rag_summarize.txt

用途：

- RAG 总结服务使用。
- 约束模型基于检索资料回答。
- 当资料不足时说明不确定。
- 输出中文。

### 12.4 supervisor_prompt.txt

用途：

- 描述 Supervisor 角色和路由标准。

当前 `StudyCopilotSupervisor` 实际采用代码关键词路由，而不是调用 LLM Supervisor Prompt 进行分类。

这个 Prompt 的价值在于：

- 保留未来升级 LLM Router 的基础。
- 让项目结构更完整。
- 方便后续迁移 LangGraph。

### 12.5 tutor_prompt.txt

用途：

- 指导 Tutor Agent 做 408 知识问答。
- 强调考试视角、常见考法、易错点。

### 12.6 planner_prompt.txt

用途：

- 指导 Planner Agent 生成学习计划。
- 强调计划可执行，避免任务过载。
- 要求结合用户画像、学习记录和错题摘要。

### 12.7 mistake_prompt.txt

用途：

- 指导 Mistake Agent 分析错题。
- 强调错因、知识点、正确推理路径和复习动作。

### 12.8 study_report_prompt.txt

用途：

- 指导 Report Agent 生成学习周报。
- 强调总结学习投入、薄弱点、完成情况和下周重点。

### 12.9 report_prompt.txt

用途：

- 保留学习周报语境的 Prompt。
- 与旧项目结构兼容。

当前实际 Report Agent 使用的是：

```text
prompts/study_report_prompt.txt
```

---

## 13. 配置系统

配置文件位于：

```text
config/
```

包括：

```text
config/rag.yml
config/chroma.yml
config/prompts.yml
config/agent.yml
```

配置统一通过：

```text
utils/config_handler.py
```

加载。

### 13.1 rag.yml

当前内容：

```yaml
chat_model_name: gpt-5.4
embedding_model_name: text-embedding-v4
```

用途：

- `chat_model_name`：聊天模型名称。
- `embedding_model_name`：Embedding 模型名称。

聊天模型在 `model/factory.py` 中通过 `ChatOpenAI` 创建。

Embedding 模型通过 `DashScopeEmbeddings` 创建。

### 13.2 chroma.yml

当前内容：

```yaml
collection_name: primebuddy_408
persist_directory: chroma_db
k: 3
data_path: data/408
md5_hex_store: md5.text
allow_knowledge_file_type: ["txt", "pdf"]

chunk_size: 200
chunk_overlap: 20
separators: ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
```

用途：

- 控制向量库名称。
- 控制知识文件路径。
- 控制文本切分参数。
- 控制检索返回数量。

### 13.3 prompts.yml

当前内容：

```yaml
main_prompt_path: prompts/main_prompt.txt
rag_summarize_prompt_path: prompts/rag_summarize.txt
report_prompt_path: prompts/report_prompt.txt
supervisor_prompt_path: prompts/supervisor_prompt.txt
tutor_prompt_path: prompts/tutor_prompt.txt
planner_prompt_path: prompts/planner_prompt.txt
mistake_prompt_path: prompts/mistake_prompt.txt
study_report_prompt_path: prompts/study_report_prompt.txt
```

用途：

- 统一维护 Prompt 路径。
- 避免在代码中硬编码 Prompt 文件。

### 13.4 agent.yml

当前内容：

```yaml
external_data_path: data/external/records.csv
```

用途：

- 保留外部数据路径配置。
- 当前 PrimeBuddy 主流程主要使用 `data/study`。

### 13.5 模型环境变量

`model/factory.py` 中 Chat Model 使用：

```python
ChatOpenAI(
    model=rag_conf["chat_model_name"],
    api_key=os.getenv("MY_API_KEY"),
    base_url=os.getenv("MY_BASE_URL"),
)
```

因此需要配置：

```text
MY_API_KEY
MY_BASE_URL
```

Embedding 使用：

```python
DashScopeEmbeddings(model=rag_conf["embedding_model_name"])
```

通常还需要配置 DashScope 相关 API Key，例如：

```text
DASHSCOPE_API_KEY
```

具体名称取决于本地 DashScope SDK 的读取方式。

---

## 14. 项目目录结构

当前核心目录结构如下：

```text
agent_my/
├── app.py
├── PrimeBuddy.md
├── PROJECT_INTRO.md
├── agent/
│   ├── react_agent.py
│   ├── study_supervisor.py
│   ├── specialists/
│   │   ├── __init__.py
│   │   ├── tutor_agent.py
│   │   ├── planner_agent.py
│   │   ├── mistake_agent.py
│   │   └── report_agent.py
│   └── tools/
│       ├── agent_tools.py
│       ├── middleware.py
│       ├── study_tools.py
│       ├── record_tools.py
│       ├── mistake_tools.py
│       └── report_tools.py
├── config/
│   ├── agent.yml
│   ├── chroma.yml
│   ├── prompts.yml
│   └── rag.yml
├── data/
│   ├── 408/
│   │   ├── data_structure.txt
│   │   ├── computer_organization.txt
│   │   ├── operating_system.txt
│   │   └── computer_network.txt
│   ├── external/
│   │   └── records.csv
│   └── study/
│       ├── user_profile.json
│       ├── learning_records.csv
│       ├── mistake_records.csv
│       └── weekly_reports.json
├── model/
│   └── factory.py
├── prompts/
│   ├── main_prompt.txt
│   ├── rag_summarize.txt
│   ├── report_prompt.txt
│   ├── supervisor_prompt.txt
│   ├── tutor_prompt.txt
│   ├── planner_prompt.txt
│   ├── mistake_prompt.txt
│   └── study_report_prompt.txt
├── rag/
│   ├── rag_service.py
│   ├── vector_store.py
│   └── chroma_db/
├── utils/
│   ├── config_handler.py
│   ├── file_handler.py
│   ├── logger_handler.py
│   ├── path_tool.py
│   └── prompt_loader.py
├── chroma_db/
├── logs/
└── md5.text
```

说明：

- `chroma_db/` 是 Chroma 持久化目录。
- `md5.text` 是知识文件加载去重记录。
- `logs/` 是运行日志目录。
- `PROJECT_INTRO.md` 当前仍是旧说明文档，PrimeBuddy 推荐阅读本文档。

---

## 15. 核心文件逐个说明

### 15.1 app.py

职责：

- 设置 Streamlit 页面标题和图标。
- 初始化 PrimeBuddy 聊天界面。
- 初始化 `StudyCopilotSupervisor`。
- 保存聊天历史。
- 接收用户输入。
- 调用 `execute_stream` 流式输出回答。

关键点：

```python
if "agent" not in st.session_state:
    st.session_state["agent"] = StudyCopilotSupervisor()
```

说明当前前端入口已经接入新 Supervisor。

### 15.2 agent/study_supervisor.py

职责：

- 初始化四个专家 Agent。
- 根据关键词判断路由。
- 将用户问题转发给对应 Agent。
- 对 general 场景返回能力介绍。
- 记录路由日志。

这是 PrimeBuddy 当前最核心的编排文件。

### 15.3 agent/specialists/

职责：

- 每个文件封装一个专家 Agent。
- 每个 Agent 使用 LangChain `create_agent`。
- 每个 Agent 加载自己的 Prompt。
- 每个 Agent 注册自己的工具集合。

统一形式：

```python
self.agent = create_agent(
    model=chat_model,
    system_prompt=load_xxx_prompts(),
    tools=[...],
    middleware=[monitor_tool, log_before_model],
)
```

### 15.4 agent/tools/

职责：

- 定义 Agent 可调用工具。
- 工具负责访问知识库或数据文件。
- 工具返回字符串或 JSON 文本。

主要工具文件：

| 文件 | 作用 |
| --- | --- |
| `study_tools.py` | 学习知识库 RAG 检索 |
| `record_tools.py` | 用户画像与学习记录读取 |
| `mistake_tools.py` | 错题查询、摘要、保存 |
| `report_tools.py` | 周报范围、输入聚合、保存 |
| `middleware.py` | 工具调用和模型调用日志 |
| `agent_tools.py` | 兼容性 RAG 工具 |

### 15.5 rag/vector_store.py

职责：

- 管理 Chroma 向量库。
- 加载知识文件。
- 文本切分。
- 写入向量库。
- 返回 retriever。

可直接运行：

```bash
conda run -n agent python rag/vector_store.py
```

用于构建或更新知识库索引。

### 15.6 rag/rag_service.py

职责：

- 封装 RAG 总结流程。
- 调用 retriever 检索资料。
- 拼接 context。
- 使用 RAG Prompt 和模型生成回答。

### 15.7 model/factory.py

职责：

- 创建 Chat Model。
- 创建 Embedding Model。
- 暴露全局对象：

```python
chat_model
embed_model
```

当前 Chat Model 使用 OpenAI-compatible 接口：

```python
ChatOpenAI
```

当前 Embedding 使用：

```python
DashScopeEmbeddings
```

### 15.8 utils/config_handler.py

职责：

- 加载 YAML 配置。
- 暴露配置字典：

```python
rag_conf
chroma_conf
prompts_conf
agent_conf
```

### 15.9 utils/prompt_loader.py

职责：

- 根据 `config/prompts.yml` 读取 Prompt 文件。
- 提供多个 Prompt 加载函数。

包括：

```python
load_system_prompts()
load_rag_prompts()
load_report_prompts()
load_supervisor_prompts()
load_tutor_prompts()
load_planner_prompts()
load_mistake_prompts()
load_study_report_prompts()
```

### 15.10 utils/file_handler.py

职责：

- 计算文件 MD5。
- 扫描指定类型文件。
- 加载 PDF。
- 加载 TXT。

### 15.11 utils/logger_handler.py

职责：

- 创建统一 logger。
- 输出控制台日志。
- 写入 `logs/agent_YYYYMMDD.log`。

### 15.12 utils/path_tool.py

职责：

- 获取项目根目录。
- 将相对路径转为绝对路径。

这保证了从不同工作目录启动时，项目仍能正确找到配置、数据和 Prompt。

---

## 16. 运行方式

### 16.1 进入项目目录

Git Bash 中：

```bash
cd /c/Users/Qizhe/Desktop/agent/agent_my
```

Windows 路径：

```text
C:\Users\Qizhe\Desktop\agent\agent_my
```

### 16.2 使用 conda 环境

本项目当前在 conda 环境 `agent` 中运行。

推荐命令格式：

```bash
conda run -n agent <command>
```

也可以先激活环境：

```bash
conda activate agent
```

然后直接运行 Python 或 Streamlit 命令。

### 16.3 配置环境变量

Chat Model 需要：

```bash
export MY_API_KEY="你的模型 API Key"
export MY_BASE_URL="你的 OpenAI-compatible Base URL"
```

Git Bash / Linux / macOS 示例：

```bash
export MY_API_KEY="xxx"
export MY_BASE_URL="https://your-base-url/v1"
```

PowerShell 示例：

```powershell
$env:MY_API_KEY="xxx"
$env:MY_BASE_URL="https://your-base-url/v1"
```

Embedding 通常需要 DashScope Key：

```bash
export DASHSCOPE_API_KEY="你的 DashScope API Key"
```

PowerShell：

```powershell
$env:DASHSCOPE_API_KEY="你的 DashScope API Key"
```

### 16.4 构建知识库向量索引

首次运行或修改 `data/408` 后，执行：

```bash
conda run -n agent python rag/vector_store.py
```

该命令会：

1. 读取 `config/chroma.yml`。
2. 扫描 `data/408`。
3. 加载 TXT/PDF 文件。
4. 切分文本。
5. 调用 Embedding。
6. 写入 Chroma。
7. 将文件 MD5 写入 `md5.text`。

如果想强制重建索引，可以删除：

```text
chroma_db/
md5.text
```

然后重新执行构建命令。

### 16.5 启动 Streamlit 应用

推荐命令：

```bash
conda run -n agent streamlit run app.py
```

启动后浏览器打开：

```text
http://localhost:8501
```

如果端口被占用，可以指定端口：

```bash
conda run -n agent streamlit run app.py --server.port 8502
```

### 16.6 推荐完整启动流程

```bash
cd /c/Users/Qizhe/Desktop/agent/agent_my
conda run -n agent python rag/vector_store.py
conda run -n agent streamlit run app.py
```

---

## 17. 演示问题与预期效果

### 17.1 Tutor Agent 演示

输入：

```text
请用 408 考研的角度讲一下操作系统中的虚拟内存，并说明常见考点。
```

预期：

- Supervisor 路由到 Tutor。
- Tutor 调用 RAG 检索操作系统资料。
- 输出虚拟内存概念、缺页中断、页表、TLB、页面置换、408 常见考法。

### 17.2 Planner Agent 演示

输入：

```text
我还有 8 周考 408，每天能学 3 小时，操作系统和计网比较弱，帮我制定下周计划。
```

预期：

- Supervisor 路由到 Planner。
- Planner 读取用户画像、学习记录和错题摘要。
- 输出下周计划、每日安排、时间分配、复盘节奏。

### 17.3 Mistake Agent 演示

输入：

```text
我做错了一道题：TCP 拥塞控制中慢开始和拥塞避免的区别是什么？我把阈值变化理解错了，帮我分析原因并给复习建议。
```

预期：

- Supervisor 路由到 Mistake。
- Mistake 调用错题工具和 RAG 工具。
- 输出知识点、错因、正确理解、相似陷阱、复习建议。

### 17.4 Report Agent 演示

输入：

```text
请生成我的本周学习报告，指出主要问题和下周重点。
```

预期：

- Supervisor 路由到 Report。
- Report 获取当前周范围。
- 聚合学习记录和错题记录。
- 输出本周学习概览、问题总结、下周重点。

---

## 18. 验证方式

### 18.1 Python 编译检查

命令：

```bash
conda run -n agent python -m compileall app.py agent config model rag utils
```

用途：

- 检查 Python 文件是否存在语法错误。

### 18.2 unittest 发现

命令：

```bash
conda run -n agent python -m unittest discover
```

当前结果说明：

- 当前项目没有正式测试文件。
- `unittest discover` 会显示 `Ran 0 tests`。

### 18.3 pytest 状态

命令：

```bash
conda run -n agent python -m pytest
```

当前环境中 `pytest` 未安装。

如果后续要补测试，可以安装 pytest 并新增测试目录。

### 18.4 路由烟测

可以用 Python 直接验证 Supervisor 路由：

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from agent.study_supervisor import StudyCopilotSupervisor; s=StudyCopilotSupervisor.__new__(StudyCopilotSupervisor); cases={'请生成我的本周学习报告':'report','这道题我错了帮我分析':'mistake','我每天3小时帮我制定计划':'planner','讲一下虚拟内存':'tutor','你好':'general'}; got={q:s.route(q).route for q in cases}; assert got==cases, got; print('route smoke checks passed')"
```

### 18.5 向量库检索验证

可以验证 408 查询是否命中相关资料：

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from rag.vector_store import VectorStoreService; vs=VectorStoreService(); docs=vs.get_retriever().invoke('操作系统 虚拟内存 缺页中断 常见考点'); text='\n'.join(d.page_content for d in docs); assert any(term in text for term in ['虚拟内存','缺页','分页','页面']); print('retrieval smoke checks passed')"
```

### 18.6 Streamlit 端到端验证

启动：

```bash
conda run -n agent streamlit run app.py
```

然后在浏览器依次输入四个演示问题。

验证目标：

- 页面能打开。
- 四类问题都能返回。
- 日志能看到 Supervisor 路由。
- Tutor 能使用 RAG。
- Planner 能使用用户画像和记录。
- Mistake 能分析错题。
- Report 能生成周报。

---

## 19. 日志与调试

### 19.1 日志位置

日志目录：

```text
logs/
```

日志文件格式：

```text
agent_YYYYMMDD.log
```

### 19.2 日志内容

当前日志会记录：

- Supervisor 路由结果。
- 工具调用名称。
- 工具调用参数。
- 工具调用成功或失败。
- 模型调用前消息数量。
- 知识库加载结果。
- 错题保存结果。
- 周报保存结果。

### 19.3 常见问题排查

#### 问题 1：模型调用失败

检查：

- `MY_API_KEY` 是否存在。
- `MY_BASE_URL` 是否正确。
- `config/rag.yml` 中模型名称是否可用。

#### 问题 2：Embedding 调用失败

检查：

- DashScope API Key 是否配置。
- 网络是否能访问 DashScope。
- `text-embedding-v4` 是否可用。

#### 问题 3：RAG 检索不到新资料

检查：

- 新文件是否放在 `data/408`。
- 文件后缀是否是 `txt` 或 `pdf`。
- 是否执行了 `python rag/vector_store.py`。
- 如果文件内容变了但 MD5 记录导致未更新，可以删除 `md5.text` 和 `chroma_db/` 后重建。

#### 问题 4：页面回答后历史丢失

检查：

- `app.py` 中是否累计所有 chunk。
- 是否将完整 `assistant` 响应写入 `st.session_state["message"]`。

#### 问题 5：路由不符合预期

检查：

- 用户问题是否命中关键词。
- `agent/study_supervisor.py` 中关键词列表是否需要补充。
- 是否存在多个关键词同时命中导致优先级影响。

---

## 20. 当前阶段边界与局限

PrimeBuddy 第一阶段是可演示的学习 Agent 原型，但不是完整生产系统。

当前边界如下：

### 20.1 用户系统

当前没有用户登录。

默认使用 demo 数据：

```text
demo_user
```

后续可以增加用户登录、用户 ID 绑定和多用户数据隔离。

### 20.2 数据存储

当前使用 CSV/JSON。

优点：

- 简单。
- 易查看。
- 适合 demo。

缺点：

- 并发写入能力弱。
- 查询能力有限。
- 不适合生产。

后续可以迁移到 SQLite 或其他数据库。

### 20.3 路由方式

当前使用关键词路由。

优点是稳定可控，缺点是语义泛化能力有限。

后续可加入 LLM Router 或 LangGraph 条件边。

### 20.4 RAG 资料规模

当前知识库是小规模 408 演示资料。

优点是稳定、可控、适合面试演示。

缺点是覆盖范围有限。

后续可以加入更完整的教材笔记、真题解析和错题知识点标签。

### 20.5 测试体系

当前没有正式测试目录。

已经进行过：

- 编译检查。
- 路由烟测。
- 检索验证。
- Streamlit 手动端到端验证。

后续建议补充：

- Supervisor 路由单元测试。
- CSV/JSON 工具测试。
- RAG 检索烟测。
- Streamlit 页面测试。

### 20.6 Report 保存格式

当前 `save_weekly_report` 中，列表字段使用中文分号 `；` 拆分。

如果后续 Prompt 改成英文分号 `;`，需要同步调整拆分逻辑。

---

## 21. 项目亮点

### 21.1 学习闭环完整

项目不是单点问答，而是覆盖：

```text
问答 -> 错题 -> 计划 -> 周报
```

这使它比普通 RAG demo 更接近真实学习场景。

### 21.2 Supervisor + 多专家 Agent

项目采用清晰的任务分工：

- Supervisor 做路由。
- Tutor 做知识问答。
- Planner 做计划。
- Mistake 做错题。
- Report 做周报。

这个结构比单 Agent 更容易维护，也更适合面试讲解。

### 21.3 RAG 与学习数据结合

Tutor 和 Mistake 可以使用知识库。

Planner 和 Report 可以使用学习记录、错题记录和用户画像。

这说明项目不是纯聊天，而是结合了外部知识和用户数据。

### 21.4 工程结构清晰

项目分层明确：

- 前端
- Supervisor
- 专家 Agent
- 工具
- RAG
- 数据
- 配置
- 日志

每个模块职责相对独立。

### 21.5 第一阶段稳定可演示

通过关键词路由和本地演示数据，系统可控性强，适合面试现场演示。

### 21.6 后续扩展路径自然

项目可以自然扩展到：

- LangGraph 编排。
- Exam Agent 模拟卷分析。
- School Agent 择校建议。
- SQLite 数据层。
- 学习趋势图表。
- 间隔复习算法。

---

## 22. 面试讲解指南

### 22.1 一分钟版本

```text
PrimeBuddy 是我基于 LangChain 和 Streamlit 实现的多 Agent 智能学习伙伴。
它的第一阶段以 408 考研为场景，支持知识问答、学习计划、错题分析和学习周报。
系统表面上是一个聊天助手，底层通过轻量 Supervisor 判断用户意图，再路由到 Tutor、Planner、Mistake、Report 四个专家 Agent。
其中 Tutor 和 Mistake 会结合 Chroma 向量库做 RAG 检索，Planner 和 Report 会读取用户画像、学习记录和错题记录，生成结构化学习建议。
这个项目的重点不是单纯聊天，而是形成“问答、错题、计划、周报”的学习闭环。
```

### 22.2 三分钟版本

```text
PrimeBuddy 是一个面向学习规划与诊断的多 Agent 项目。
我最初的项目只是一个基础 LangChain/Streamlit/RAG demo，所以我把它改造成了一个更适合面试展示的学习 Agent 系统。

当前第一阶段选择 408 考研作为落地场景，因为 408 的知识体系清晰，包含数据结构、计组、操作系统和计网，适合做知识问答、错题分析和学习计划。

架构上，我没有把所有能力写进一个大 Prompt，而是设计了一个轻量 Supervisor。
用户输入后，Supervisor 会根据关键词判断任务类型，然后路由到四个专家 Agent：Tutor 负责知识问答，Planner 负责学习计划，Mistake 负责错题分析，Report 负责学习周报。

Tutor Agent 会调用 RAG 工具，从本地 408 知识库中检索资料，再生成考试导向的回答。
Planner Agent 会读取用户画像、学习记录和错题摘要，生成可执行计划。
Mistake Agent 会结合错题记录和知识库分析错因。
Report Agent 会聚合本周学习记录和错题记录，生成学习周报。

数据层第一阶段使用 CSV 和 JSON，方便演示和查看。知识库使用 Chroma 存储向量，Embedding 使用 DashScope，聊天模型通过 OpenAI-compatible 接口调用。

这个项目的亮点是它形成了一个学习闭环：知识问答、错题诊断、薄弱点识别、学习计划和周报复盘。后续我计划把轻量 Supervisor 迁移到 LangGraph，并增加模拟考试分析、SQLite 数据层和择校建议 Agent。
```

### 22.3 技术深挖版本

可以从以下角度展开：

1. **为什么使用多 Agent**
   - 不同任务的 Prompt、工具和输出结构不同。
   - 拆分后职责更清晰。
   - 减少单 Agent 工具过多导致的误调用。

2. **为什么第一阶段使用轻量 Supervisor**
   - 保证稳定演示。
   - 路由逻辑可解释。
   - 后续可迁移 LangGraph。

3. **RAG 如何实现**
   - `VectorStoreService` 加载 `data/408`。
   - 使用文本切分器切分资料。
   - 使用 Embedding 写入 Chroma。
   - 查询时 retriever 返回 top-k 文档。
   - `RagSummarizeService` 将资料拼接进 Prompt。

4. **工具如何设计**
   - 每个工具只负责一个明确动作。
   - 返回 JSON 字符串，方便模型理解。
   - 每个专家 Agent 只注册需要的工具。

5. **数据为什么用 CSV/JSON**
   - Phase 1 重点是架构和演示。
   - CSV/JSON 易读、易改、无需数据库部署。
   - 后续可以迁移 SQLite。

6. **项目如何扩展**
   - 路由升级为 LangGraph。
   - 数据层升级为数据库。
   - 加 Exam Agent 做试卷分析。
   - 加 School Agent 做择校建议。

---

## 23. 面试官可能追问与回答方向

### 23.1 为什么不用一个 Agent 解决所有问题？

可以回答：

```text
一个 Agent 当然可以做，但它的 Prompt 会变得很长，工具集合也会变得很复杂。
学习问答、计划生成、错题分析和周报生成的目标不同，输出结构也不同。
所以我把它们拆成四个专家 Agent，让每个 Agent 只关注自己的任务。
这样 Prompt 更清晰，工具调用更稳定，后续维护和扩展也更容易。
```

### 23.2 为什么不用 LangGraph？

可以回答：

```text
我把 LangGraph 放在 Phase 1.5。
第一阶段的目标是先把学习闭环跑通，所以我使用轻量 Supervisor 做确定性路由。
这样更容易调试，也能保证演示稳定。
等四个专家 Agent 的输入输出稳定后，再迁移成 LangGraph 节点和条件边会更自然。
```

### 23.3 RAG 如何降低幻觉？

可以回答：

```text
Tutor Agent 不直接依赖模型自身知识回答，而是先通过工具检索本地 408 知识库。
RAG 服务会把召回的参考资料拼接进 Prompt，并要求模型基于资料回答。
如果资料不足，Prompt 会要求模型说明不确定，而不是编造。
这样可以让回答更贴近项目准备的知识库。
```

### 23.4 为什么用 CSV/JSON，不用数据库？

可以回答：

```text
第一阶段是面试演示原型，我优先保证数据可读、可改、可展示。
CSV/JSON 不需要额外部署，面试官也可以直接打开看用户画像、学习记录和错题记录。
后续如果做多用户、并发写入和复杂查询，我会迁移到 SQLite。
```

### 23.5 如果用户问题同时像计划又像周报怎么办？

可以回答：

```text
当前 Supervisor 有明确优先级：report > mistake > planner > tutor。
比如“本周复盘并安排下周计划”会优先进入 Report，因为它需要先总结本周情况。
如果后续要更精细，可以引入 LLM 分类器和置信度机制，或者让系统追问用户更想要周报还是计划。
```

### 23.6 这个项目和普通 RAG 项目有什么区别？

可以回答：

```text
普通 RAG 项目通常只做知识问答。
PrimeBuddy 不只做知识问答，还结合学习记录和错题记录生成计划和周报。
它的核心是学习闭环，而不是单次问答。
另外它使用 Supervisor + 多专家 Agent，让不同任务由不同 Agent 处理。
```

### 23.7 如何判断项目是否真的跑通？

可以回答：

```text
我做了几类验证。
第一是 Python 编译检查。
第二是 Supervisor 路由烟测，确认不同问题能分到不同 Agent。
第三是 RAG 检索验证，确认 408 查询能命中相关资料。
第四是 Streamlit 端到端验证，分别测试 Tutor、Planner、Mistake 和 Report 四类 demo 问题。
```

---

## 24. 后续扩展路线

### 24.1 Phase 1.5：迁移 LangGraph

目标：

- 将 Supervisor 改造成 LangGraph 图。
- 每个专家 Agent 作为一个节点。
- 路由逻辑变成条件边。
- 增加路由置信度。
- 对不明确意图进行追问。

可能结构：

```text
User Input
  ↓
Router Node
  ↓
Tutor / Planner / Mistake / Report Node
  ↓
Final Response Node
```

### 24.2 Phase 2：增强学习分析能力

可增加：

1. **Exam Agent**
   - 支持模拟卷分析。
   - 根据分数和错题定位薄弱章节。
   - 给出提分策略。

2. **SQLite 数据层**
   - 替换 CSV/JSON。
   - 支持多用户。
   - 支持历史查询和统计。

3. **学习图表**
   - 展示每周学习时长。
   - 展示各科投入分布。
   - 展示错题知识点分布。

4. **间隔复习算法**
   - 引入 SM-2 或类似机制。
   - 根据错题状态安排二刷、三刷。

### 24.3 Phase 3：扩展考研决策场景

可增加：

1. **School Agent**
   - 根据用户分数、地区、专业偏好做择校建议。

2. **招生信息检索**
   - 检索院校公开招生信息。
   - 标注来源。

3. **复试模拟**
   - 根据院校方向生成复试问答。
   - 进行模拟面试。

4. **长期学习档案**
   - 汇总多个阶段的学习表现。
   - 给出长期趋势分析。

---

## 25. 总结

PrimeBuddy 当前已经从一个基础 demo 改造成了一个具有清晰学习场景、完整任务闭环和多 Agent 架构的智能学习伙伴。

它的核心特点是：

1. 以 408 考研为第一阶段场景，但项目名和架构不绑定 408。
2. 使用轻量 Supervisor 将用户问题路由给四个专家 Agent。
3. Tutor、Planner、Mistake、Report 分别处理知识问答、学习计划、错题分析和学习周报。
4. RAG 知识库提供 408 资料检索能力。
5. CSV/JSON 数据层提供用户画像、学习记录、错题记录和周报记录。
6. Streamlit 提供可交互聊天界面。
7. YAML 配置、Prompt 文件、工具系统和日志模块保证项目结构清晰。

从面试展示角度看，PrimeBuddy 的讲解重点不是“我做了一个聊天机器人”，而是：

```text
我基于 LangChain 构建了一个多 Agent 学习助手。
它通过 Supervisor 协调多个专家 Agent，并结合 RAG 和学习数据，形成了从知识问答到错题诊断、学习计划和周报复盘的学习闭环。
```

这也是 PrimeBuddy 相比普通 RAG demo 或普通聊天助手更有展示价值的地方。