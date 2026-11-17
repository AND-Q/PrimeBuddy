# PrimeBuddy P0 Interview Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make PrimeBuddy's Phase 1 demo more reliable and interview-ready by adding repeatable tests, tightening routing, controlling write-side effects, cleaning RAG debug output, fixing Chroma path resolution, and adding a one-command validation script.

**Architecture:** Keep the existing lightweight Supervisor + four specialist Agents architecture. Add focused unittest coverage around deterministic code paths, make tool side effects opt-in through explicit confirmation parameters, and expose a small validation script that compiles code, runs tests, and optionally checks retrieval when credentials are available.

**Tech Stack:** Python stdlib `unittest`, Streamlit, LangChain `create_agent`, Chroma, DashScope Embeddings, OpenAI-compatible Chat Model, YAML config, CSV/JSON local data.

---

## File Structure

### Files to modify

- `agent/study_supervisor.py` — tighten deterministic routing so generic summary words do not steal mistake/planner/tutor queries.
- `agent/tools/mistake_tools.py` — require explicit `confirm_save=True` before appending a mistake record.
- `agent/tools/report_tools.py` — require explicit `confirm_save=True` before writing a weekly report and add robust semicolon splitting.
- `prompts/mistake_prompt.txt` — tell the Agent to call the save tool only after explicit user confirmation.
- `prompts/study_report_prompt.txt` — tell the Agent to call the save tool only after explicit user confirmation.
- `rag/rag_service.py` — replace unconditional `print` debug output with config-gated logger debug output.
- `rag/vector_store.py` — resolve Chroma `persist_directory` through `get_abs_path`.
- `config/rag.yml` — add `debug_rag_prompt: false`.
- `PrimeBuddy.md` — add the new validation command to the verification section.

### Files to create

- `tests/test_study_supervisor.py` — route regression tests and route boundary tests.
- `tests/test_mistake_tools.py` — save guard tests for mistake records.
- `tests/test_report_tools.py` — save guard tests and semicolon parsing tests for reports.
- `tests/test_rag_config.py` — tests for RAG prompt logging behavior and absolute Chroma path resolution.
- `scripts/validate_primebuddy.py` — one-command local validation script.

---

## Task 1: Add Supervisor Route Regression Tests and Tighten Boundary Routing

**Files:**
- Create: `tests/test_study_supervisor.py`
- Modify: `agent/study_supervisor.py`

- [ ] **Step 1: Write the failing route tests**

Create `tests/test_study_supervisor.py` with this exact content:

```python
import unittest

from agent.study_supervisor import StudyCopilotSupervisor


class StudyCopilotSupervisorRouteTest(unittest.TestCase):
    def setUp(self):
        self.supervisor = StudyCopilotSupervisor.__new__(StudyCopilotSupervisor)

    def assert_route(self, query: str, expected_route: str):
        actual = self.supervisor.route(query).route
        self.assertEqual(actual, expected_route, msg=f"query={query!r}")

    def test_original_demo_routes(self):
        cases = {
            "请生成我的本周学习报告": "report",
            "这道题我错了帮我分析": "mistake",
            "我每天3小时帮我制定计划": "planner",
            "讲一下虚拟内存": "tutor",
            "你好": "general",
        }

        for query, expected_route in cases.items():
            with self.subTest(query=query):
                self.assert_route(query, expected_route)

    def test_boundary_routes(self):
        cases = {
            "本周复盘并安排下周计划": "report",
            "总结一下我错题里的操作系统问题": "mistake",
            "我总是学不会虚拟内存，该怎么复习": "planner",
            "虚拟内存是什么，常见考法有哪些": "tutor",
            "这道页表题正确答案为什么是 B": "mistake",
        }

        for query, expected_route in cases.items():
            with self.subTest(query=query):
                self.assert_route(query, expected_route)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the route tests and verify the boundary failure**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_study_supervisor -v
```

Expected: at least one failure, specifically `"总结一下我错题里的操作系统问题"` routes to `report` before the implementation change.

- [ ] **Step 3: Tighten the route implementation**

Replace the `route()` method in `agent/study_supervisor.py` with this implementation:

```python
    def route(self, query: str) -> RouteResult:
        normalized_query = query.strip().lower()

        report_keywords = ["周报", "学习报告", "本周", "这周", "阶段报告", "下周重点"]
        report_context_keywords = ["总结", "复盘"]
        report_time_keywords = ["本周", "这周", "这段时间", "阶段", "周"]
        mistake_keywords = ["错题", "错了", "做错", "选错", "正确答案", "错因", "为什么错", "不会做", "二刷"]
        planner_keywords = ["计划", "安排", "规划", "复习", "每天", "每周", "还有", "目标分", "冲刺", "进度", "怎么学"]
        tutor_keywords = ["讲一下", "解释", "是什么", "区别", "考法", "知识点", "例题", "概念", "原理", "流程"]

        is_report_query = self.has_any_keyword(normalized_query, report_keywords) or (
            self.has_any_keyword(normalized_query, report_context_keywords)
            and self.has_any_keyword(normalized_query, report_time_keywords)
        )

        if is_report_query:
            return RouteResult("report", "命中周报/阶段复盘类关键词")
        if self.has_any_keyword(normalized_query, mistake_keywords):
            return RouteResult("mistake", "命中错题/错因类关键词")
        if self.has_any_keyword(normalized_query, planner_keywords):
            return RouteResult("planner", "命中学习计划/复习安排类关键词")
        if self.has_any_keyword(normalized_query, tutor_keywords):
            return RouteResult("tutor", "命中知识问答类关键词")

        return RouteResult("general", "未命中明确专家路由关键词")
```

- [ ] **Step 4: Run the route tests again**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_study_supervisor -v
```

Expected: all tests pass.

- [ ] **Step 5: Run the existing route smoke command**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from agent.study_supervisor import StudyCopilotSupervisor; s=StudyCopilotSupervisor.__new__(StudyCopilotSupervisor); cases={'请生成我的本周学习报告':'report','这道题我错了帮我分析':'mistake','我每天3小时帮我制定计划':'planner','讲一下虚拟内存':'tutor','你好':'general'}; got={q:s.route(q).route for q in cases}; assert got==cases, got; print('route smoke checks passed')"
```

Expected: `route smoke checks passed`.

- [ ] **Step 6: Commit checkpoint if allowed**

This workspace is currently not a git repository. If execution happens inside a git repository and the user has explicitly requested commits, run:

```bash
git add agent/study_supervisor.py tests/test_study_supervisor.py
git commit -m "test: cover PrimeBuddy supervisor routing"
```

---

## Task 2: Require Explicit Confirmation Before Saving Mistake Records

**Files:**
- Create: `tests/test_mistake_tools.py`
- Modify: `agent/tools/mistake_tools.py`
- Modify: `prompts/mistake_prompt.txt`

- [ ] **Step 1: Write failing tests for mistake save side effects**

Create `tests/test_mistake_tools.py` with this exact content:

```python
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.tools import mistake_tools


class SaveMistakeRecordTest(unittest.TestCase):
    def write_records_file(self, path: Path):
        rows = [
            {
                "id": "M001",
                "date": "2026-05-01",
                "user_id": "demo_user",
                "subject": "操作系统",
                "chapter": "虚拟内存",
                "question": "页和页框的区别是什么？",
                "user_answer": "一样",
                "correct_answer": "页是逻辑单位，页框是物理单位",
                "error_reason": "概念混淆",
                "knowledge_point": "分页存储",
                "status": "待复习",
            }
        ]
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=mistake_tools.MISTAKE_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def read_rows(self, path: Path):
        with path.open("r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_save_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            records_path = Path(tmpdir) / "mistake_records.csv"
            self.write_records_file(records_path)

            with patch.object(mistake_tools, "get_abs_path", return_value=str(records_path)):
                result = mistake_tools.save_mistake_record.invoke(
                    {
                        "user_id": "demo_user",
                        "subject": "计算机网络",
                        "chapter": "拥塞控制",
                        "question": "慢开始和拥塞避免的区别是什么？",
                        "user_answer": "阈值不变",
                        "correct_answer": "达到阈值后从指数增长切换为线性增长",
                        "error_reason": "阈值变化理解错误",
                        "knowledge_point": "TCP 拥塞控制",
                    }
                )

            payload = json.loads(result)
            self.assertFalse(payload["saved"])
            self.assertEqual(len(self.read_rows(records_path)), 1)

    def test_save_writes_record_when_confirmed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            records_path = Path(tmpdir) / "mistake_records.csv"
            self.write_records_file(records_path)

            with patch.object(mistake_tools, "get_abs_path", return_value=str(records_path)):
                result = mistake_tools.save_mistake_record.invoke(
                    {
                        "user_id": "demo_user",
                        "subject": "计算机网络",
                        "chapter": "拥塞控制",
                        "question": "慢开始和拥塞避免的区别是什么？",
                        "user_answer": "阈值不变",
                        "correct_answer": "达到阈值后从指数增长切换为线性增长",
                        "error_reason": "阈值变化理解错误",
                        "knowledge_point": "TCP 拥塞控制",
                        "confirm_save": True,
                    }
                )

            payload = json.loads(result)
            rows = self.read_rows(records_path)
            self.assertTrue(payload["saved"])
            self.assertEqual(payload["id"], "M002")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[-1]["id"], "M002")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the mistake tool tests and verify failure**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_mistake_tools -v
```

Expected: failure because `save_mistake_record` does not yet accept `confirm_save` and currently writes immediately.

- [ ] **Step 3: Add the confirmation guard to the save tool**

In `agent/tools/mistake_tools.py`, replace the `@tool` description and function signature/body for `save_mistake_record` with this version:

```python
@tool(description="追加保存一条错题记录，并返回保存后的错题ID。只有用户明确要求保存时，confirm_save才应传True；否则不要写入文件。")
def save_mistake_record(
        user_id: str,
        subject: str,
        chapter: str,
        question: str,
        user_answer: str,
        correct_answer: str,
        error_reason: str,
        knowledge_point: str,
        status: str = "待复习",
        confirm_save: bool = False,
) -> str:
    if not confirm_save:
        return to_json_text(
            {
                "saved": False,
                "reason": "需要用户明确确认保存后才能写入错题记录。",
            }
        )

    records_path = get_abs_path(MISTAKE_RECORDS_PATH)

    with open(records_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    mistake_id = next_mistake_id(rows)
    row = {
        "id": mistake_id,
        "date": date.today().isoformat(),
        "user_id": user_id,
        "subject": subject,
        "chapter": chapter,
        "question": question,
        "user_answer": user_answer,
        "correct_answer": correct_answer,
        "error_reason": error_reason,
        "knowledge_point": knowledge_point,
        "status": status,
    }

    with open(records_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MISTAKE_FIELDS)
        writer.writerow(row)

    logger.info(f"[save_mistake_record]已保存错题：{mistake_id}")
    return to_json_text({"saved": True, "id": mistake_id, "record": row})
```

- [ ] **Step 4: Update the Mistake Agent prompt**

Open `prompts/mistake_prompt.txt` and add this exact rule near the tool-use instructions:

```text
只有当用户明确说“保存”“记录到错题本”“加入错题记录”等保存意图时，才允许调用 save_mistake_record，并且必须传入 confirm_save=true。普通错题分析只给出“建议保存”的说明，不要写入错题记录。
```

- [ ] **Step 5: Run the mistake tool tests again**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_mistake_tools -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit checkpoint if allowed**

This workspace is currently not a git repository. If execution happens inside a git repository and the user has explicitly requested commits, run:

```bash
git add agent/tools/mistake_tools.py prompts/mistake_prompt.txt tests/test_mistake_tools.py
git commit -m "fix: require confirmation before saving mistakes"
```

---

## Task 3: Require Explicit Confirmation Before Saving Weekly Reports and Support Both Semicolon Styles

**Files:**
- Create: `tests/test_report_tools.py`
- Modify: `agent/tools/report_tools.py`
- Modify: `prompts/study_report_prompt.txt`

- [ ] **Step 1: Write failing tests for report save guard and semicolon parsing**

Create `tests/test_report_tools.py` with this exact content:

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.tools import report_tools


class ReportToolsTest(unittest.TestCase):
    def test_split_list_field_accepts_chinese_and_english_semicolons(self):
        result = report_tools.split_list_field("优势一；优势二; 优势三；  ;")
        self.assertEqual(result, ["优势一", "优势二", "优势三"])

    def test_save_weekly_report_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_path = Path(tmpdir) / "weekly_reports.json"
            reports_path.write_text("[]", encoding="utf-8")

            with patch.object(report_tools, "get_abs_path", return_value=str(reports_path)):
                result = report_tools.save_weekly_report.invoke(
                    {
                        "user_id": "demo_user",
                        "week_start": "2026-05-11",
                        "week_end": "2026-05-17",
                        "summary": "本周完成操作系统复习。",
                        "strengths": "坚持完成每日任务；错题复盘及时",
                        "weaknesses": "计网投入不足; 虚拟内存仍混淆",
                        "recommended_next_week_plan": "补计网；二刷虚拟内存",
                        "risk_flags": "时间分配不均",
                    }
                )

            payload = json.loads(result)
            self.assertFalse(payload["saved"])
            self.assertEqual(json.loads(reports_path.read_text(encoding="utf-8")), [])

    def test_save_weekly_report_writes_when_confirmed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_path = Path(tmpdir) / "weekly_reports.json"
            reports_path.write_text("[]", encoding="utf-8")

            with patch.object(report_tools, "get_abs_path", return_value=str(reports_path)):
                result = report_tools.save_weekly_report.invoke(
                    {
                        "user_id": "demo_user",
                        "week_start": "2026-05-11",
                        "week_end": "2026-05-17",
                        "summary": "本周完成操作系统复习。",
                        "strengths": "坚持完成每日任务；错题复盘及时",
                        "weaknesses": "计网投入不足; 虚拟内存仍混淆",
                        "recommended_next_week_plan": "补计网；二刷虚拟内存",
                        "risk_flags": "时间分配不均",
                        "confirm_save": True,
                    }
                )

            payload = json.loads(result)
            reports = json.loads(reports_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["saved"])
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0]["weaknesses"], ["计网投入不足", "虚拟内存仍混淆"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the report tool tests and verify failure**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_report_tools -v
```

Expected: failure because `split_list_field` does not exist and `save_weekly_report` currently writes immediately.

- [ ] **Step 3: Add robust list parsing and the report save guard**

In `agent/tools/report_tools.py`, add this helper after `summarize_mistake_records`:

```python
def split_list_field(value: str) -> list[str]:
    normalized = value.replace(";", "；")
    return [item.strip() for item in normalized.split("；") if item.strip()]
```

Then replace the `@tool` description and `save_weekly_report` function with this version:

```python
@tool(description="保存一份学习周报到weekly_reports.json，返回保存结果。只有用户明确要求保存时，confirm_save才应传True；strengths、weaknesses、recommended_next_week_plan和risk_flags可使用中文或英文分号分隔多项。")
def save_weekly_report(
        user_id: str,
        week_start: str,
        week_end: str,
        summary: str,
        strengths: str,
        weaknesses: str,
        recommended_next_week_plan: str,
        risk_flags: str,
        confirm_save: bool = False,
) -> str:
    if not confirm_save:
        return to_json_text(
            {
                "saved": False,
                "reason": "需要用户明确确认保存后才能写入学习周报。",
            }
        )

    reports_path = get_abs_path(WEEKLY_REPORTS_PATH)

    with open(reports_path, "r", encoding="utf-8") as f:
        reports = json.load(f)

    report = {
        "user_id": user_id,
        "week_start": week_start,
        "week_end": week_end,
        "summary": summary,
        "strengths": split_list_field(strengths),
        "weaknesses": split_list_field(weaknesses),
        "recommended_next_week_plan": split_list_field(recommended_next_week_plan),
        "risk_flags": split_list_field(risk_flags),
    }
    reports.append(report)

    with open(reports_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

    logger.info(f"[save_weekly_report]已保存用户：{user_id}在{week_start}到{week_end}的学习周报")
    return to_json_text({"saved": True, "report": report})
```

- [ ] **Step 4: Update the Report Agent prompt**

Open `prompts/study_report_prompt.txt` and add this exact rule near the tool-use instructions:

```text
只有当用户明确说“保存周报”“记录这份周报”“写入周报记录”等保存意图时，才允许调用 save_weekly_report，并且必须传入 confirm_save=true。普通生成周报只输出周报内容，不要写入 weekly_reports.json。
```

- [ ] **Step 5: Run the report tool tests again**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_report_tools -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit checkpoint if allowed**

This workspace is currently not a git repository. If execution happens inside a git repository and the user has explicitly requested commits, run:

```bash
git add agent/tools/report_tools.py prompts/study_report_prompt.txt tests/test_report_tools.py
git commit -m "fix: guard weekly report writes"
```

---

## Task 4: Remove Unconditional RAG Prompt Printing and Resolve Chroma Path Absolutely

**Files:**
- Create: `tests/test_rag_config.py`
- Modify: `rag/rag_service.py`
- Modify: `rag/vector_store.py`
- Modify: `config/rag.yml`

- [ ] **Step 1: Write failing tests for RAG debug output and Chroma path resolution**

Create `tests/test_rag_config.py` with this exact content:

```python
import os
import unittest
from unittest.mock import Mock, patch

from rag import rag_service
from rag import vector_store


class RagConfigTest(unittest.TestCase):
    def test_maybe_log_prompt_does_not_print_when_debug_disabled(self):
        prompt = Mock()
        prompt.to_string.return_value = "sensitive prompt text"

        with patch.dict(rag_service.rag_conf, {"debug_rag_prompt": False}, clear=False):
            with patch("builtins.print") as print_mock:
                result = rag_service.maybe_log_prompt(prompt)

        self.assertIs(result, prompt)
        print_mock.assert_not_called()
        prompt.to_string.assert_not_called()

    def test_maybe_log_prompt_logs_when_debug_enabled(self):
        prompt = Mock()
        prompt.to_string.return_value = "debug prompt text"

        with patch.dict(rag_service.rag_conf, {"debug_rag_prompt": True}, clear=False):
            with patch.object(rag_service.logger, "debug") as debug_mock:
                result = rag_service.maybe_log_prompt(prompt)

        self.assertIs(result, prompt)
        debug_mock.assert_called_once()
        prompt.to_string.assert_called_once()

    def test_chroma_persist_directory_is_absolute(self):
        with patch.dict(vector_store.chroma_conf, {"persist_directory": "chroma_db"}, clear=False):
            persist_directory = vector_store.get_chroma_persist_directory()

        self.assertTrue(os.path.isabs(persist_directory))
        self.assertTrue(persist_directory.endswith("chroma_db"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the RAG config tests and verify failure**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_rag_config -v
```

Expected: failure because `maybe_log_prompt` and `get_chroma_persist_directory` do not exist yet.

- [ ] **Step 3: Add the debug flag to config**

Modify `config/rag.yml` so it contains:

```yaml
chat_model_name: gpt-5.4
embedding_model_name: text-embedding-v4
debug_rag_prompt: false
```

- [ ] **Step 4: Replace unconditional prompt printing with gated logging**

In `rag/rag_service.py`, replace the import block and `print_prompt` function with this version:

```python
"""
总结服务类：用户提问，搜索参考资料，将提问和参考资料提交给模型，让模型总结回复
"""
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompts
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model
from utils.config_handler import rag_conf
from utils.logger_handler import logger


def maybe_log_prompt(prompt):
    if rag_conf.get("debug_rag_prompt", False):
        logger.debug("[RagSummarizeService]最终Prompt:\n%s", prompt.to_string())
    return prompt
```

Then change `_init_chain()` in `rag/rag_service.py` to:

```python
    def _init_chain(self):
        chain = self.prompt_template | maybe_log_prompt | self.model | StrOutputParser()
        return chain
```

- [ ] **Step 5: Resolve Chroma path through project root**

In `rag/vector_store.py`, add this helper above `class VectorStoreService`:

```python
def get_chroma_persist_directory() -> str:
    return get_abs_path(chroma_conf["persist_directory"])
```

Then change the `Chroma(...)` call in `VectorStoreService.__init__()` from:

```python
persist_directory=chroma_conf["persist_directory"],
```

to:

```python
persist_directory=get_chroma_persist_directory(),
```

- [ ] **Step 6: Run the RAG config tests again**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_rag_config -v
```

Expected: all tests pass.

- [ ] **Step 7: Run compile check**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m compileall app.py agent config model rag utils
```

Expected: compile completes successfully and does not print syntax errors.

- [ ] **Step 8: Commit checkpoint if allowed**

This workspace is currently not a git repository. If execution happens inside a git repository and the user has explicitly requested commits, run:

```bash
git add rag/rag_service.py rag/vector_store.py config/rag.yml tests/test_rag_config.py
git commit -m "fix: gate rag debug output"
```

---

## Task 5: Add One-Command Local Validation Script

**Files:**
- Create: `scripts/validate_primebuddy.py`
- Modify: `PrimeBuddy.md`

- [ ] **Step 1: Create the validation script**

Create `scripts/validate_primebuddy.py` with this exact content:

```python
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str], description: str) -> bool:
    print(f"\n==> {description}")
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"FAILED: {description}")
        return False
    print(f"PASSED: {description}")
    return True


def run_route_smoke() -> bool:
    print("\n==> Supervisor route smoke check")
    try:
        from agent.study_supervisor import StudyCopilotSupervisor

        supervisor = StudyCopilotSupervisor.__new__(StudyCopilotSupervisor)
        cases = {
            "请生成我的本周学习报告": "report",
            "这道题我错了帮我分析": "mistake",
            "我每天3小时帮我制定计划": "planner",
            "讲一下虚拟内存": "tutor",
            "你好": "general",
            "本周复盘并安排下周计划": "report",
            "总结一下我错题里的操作系统问题": "mistake",
        }
        got = {query: supervisor.route(query).route for query in cases}
        assert got == cases, got
    except Exception as exc:
        print(f"FAILED: Supervisor route smoke check: {exc}")
        return False

    print("PASSED: Supervisor route smoke check")
    return True


def run_optional_retrieval_smoke() -> bool:
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("\n==> Retrieval smoke check skipped because DASHSCOPE_API_KEY is not set")
        return True

    print("\n==> Retrieval smoke check")
    try:
        from rag.vector_store import VectorStoreService

        vector_store = VectorStoreService()
        docs = vector_store.get_retriever().invoke("操作系统 虚拟内存 缺页中断 常见考点")
        text = "\n".join(doc.page_content for doc in docs)
        assert any(term in text for term in ["虚拟内存", "缺页", "分页", "页面"]), text
    except Exception as exc:
        print(f"FAILED: Retrieval smoke check: {exc}")
        return False

    print("PASSED: Retrieval smoke check")
    return True


def main() -> int:
    checks = [
        run_command(
            [sys.executable, "-m", "compileall", "app.py", "agent", "config", "model", "rag", "utils"],
            "Python compile check",
        ),
        run_command(
            [sys.executable, "-m", "unittest", "discover", "-v"],
            "unittest discovery",
        ),
        run_route_smoke(),
        run_optional_retrieval_smoke(),
    ]

    if all(checks):
        print("\nAll PrimeBuddy validation checks passed.")
        return 0

    print("\nPrimeBuddy validation failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the validation script**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python scripts/validate_primebuddy.py
```

Expected:

```text
PASSED: Python compile check
PASSED: unittest discovery
PASSED: Supervisor route smoke check
```

Expected retrieval behavior:

- If `DASHSCOPE_API_KEY` is not set, the script prints that retrieval smoke check was skipped.
- If `DASHSCOPE_API_KEY` is set and the Chroma index is built, retrieval smoke check passes.

- [ ] **Step 3: Document the validation command**

In `PrimeBuddy.md`, under section `18. 验证方式`, add this subsection before `18.1 Python 编译检查`:

```markdown
### 18.0 一键本地验收

推荐先运行统一验收脚本：

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python scripts/validate_primebuddy.py
```

该脚本会依次执行 Python 编译检查、unittest 自动发现、Supervisor 路由烟测，并在 `DASHSCOPE_API_KEY` 已配置时执行 RAG 检索烟测。
```

- [ ] **Step 4: Run the validation script again**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python scripts/validate_primebuddy.py
```

Expected: all required checks pass, and retrieval is either passed or explicitly skipped because `DASHSCOPE_API_KEY` is missing.

- [ ] **Step 5: Commit checkpoint if allowed**

This workspace is currently not a git repository. If execution happens inside a git repository and the user has explicitly requested commits, run:

```bash
git add scripts/validate_primebuddy.py PrimeBuddy.md
git commit -m "chore: add PrimeBuddy validation script"
```

---

## Task 6: Run Full Verification and Manual Demo Checks

**Files:**
- No file changes expected.

- [ ] **Step 1: Run focused unit tests**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_study_supervisor tests.test_mistake_tools tests.test_report_tools tests.test_rag_config -v
```

Expected: all tests pass.

- [ ] **Step 2: Run full unittest discovery**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest discover -v
```

Expected: all discovered tests pass.

- [ ] **Step 3: Run compile check**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m compileall app.py agent config model rag utils
```

Expected: compile completes successfully and does not print syntax errors.

- [ ] **Step 4: Run unified validation**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python scripts/validate_primebuddy.py
```

Expected: all required checks pass.

- [ ] **Step 5: Start the Streamlit app for manual demo validation**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent streamlit run app.py --server.port 8502
```

Expected: Streamlit starts and prints a local URL for port `8502`.

- [ ] **Step 6: Validate the four golden demo prompts manually**

In the Streamlit UI, send these prompts one by one:

```text
请用 408 考研的角度讲一下操作系统中的虚拟内存，并说明常见考点。
```

```text
我还有 8 周考 408，每天能学 3 小时，操作系统和计网比较弱，帮我制定下周计划。
```

```text
我做错了一道题：TCP 拥塞控制中慢开始和拥塞避免的区别是什么？我把阈值变化理解错了，帮我分析原因并给复习建议。
```

```text
请生成我的本周学习报告，指出主要问题和下周重点。
```

Expected:

- Tutor returns a 408-oriented knowledge explanation.
- Planner returns a structured plan.
- Mistake returns analysis and does not save a mistake unless the prompt explicitly asks to save it.
- Report returns a weekly report and does not write `weekly_reports.json` unless the prompt explicitly asks to save it.
- Chat history retains complete assistant responses after rerun.

- [ ] **Step 7: Stop Streamlit**

Use `Ctrl+C` in the terminal running Streamlit.

- [ ] **Step 8: Commit final checkpoint if allowed**

This workspace is currently not a git repository. If execution happens inside a git repository and the user has explicitly requested commits, run:

```bash
git status --short
git add agent/study_supervisor.py agent/tools/mistake_tools.py agent/tools/report_tools.py rag/rag_service.py rag/vector_store.py config/rag.yml prompts/mistake_prompt.txt prompts/study_report_prompt.txt tests/test_study_supervisor.py tests/test_mistake_tools.py tests/test_report_tools.py tests/test_rag_config.py scripts/validate_primebuddy.py PrimeBuddy.md
git commit -m "chore: harden PrimeBuddy interview demo"
```

---

## Self-Review

### Spec coverage

- Repeatable tests: Task 1, Task 2, Task 3, Task 4, Task 6.
- One-command validation: Task 5.
- Route boundary improvements: Task 1.
- Mistake save side-effect control: Task 2.
- Weekly report save side-effect control: Task 3.
- RAG debug output cleanup: Task 4.
- Chroma absolute path resolution: Task 4.
- Weekly report semicolon compatibility: Task 3.
- Documentation of validation command: Task 5.

### Placeholder scan

This plan contains concrete file paths, concrete test code, concrete implementation snippets, and exact commands. It does not rely on unspecified placeholder work.

### Type consistency

- `confirm_save: bool = False` is used consistently in `save_mistake_record` and `save_weekly_report` tests and implementation snippets.
- `split_list_field(value: str) -> list[str]` is defined before test expectations rely on it.
- `maybe_log_prompt(prompt)` and `get_chroma_persist_directory()` names match tests and implementation snippets.
