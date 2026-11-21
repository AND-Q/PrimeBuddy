"""CLI runner for PrimeBuddy evaluation suites.

Usage:
    python -m evals.run --target v1 --suite all
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from evals.metrics import (
    E2ERecord,
    RetrievalRecord,
    SkillRecord,
    compute_e2e_metrics,
    compute_retrieval_metrics,
    compute_skill_metrics,
    evaluate_retrieval_case,
)
from evals.schemas import RetrievalCase, SkillSelectionCase
from evals.targets import load_target

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = PROJECT_ROOT / "evals" / "datasets"
REPORTS_DIR = PROJECT_ROOT / "evals" / "reports"
PROTECTED_DATA_FILES = [
    PROJECT_ROOT / "data" / "study" / "mistake_records.csv",
    PROJECT_ROOT / "data" / "study" / "weekly_reports.json",
]


def load_skill_cases(path: Path = DATASETS_DIR / "skill_selection.jsonl") -> list[SkillSelectionCase]:
    cases: list[SkillSelectionCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        cases.append(
            SkillSelectionCase(
                id=row["id"],
                query=row["query"],
                expected_any=list(row["expected_any"]),
                category=row["category"],
                tags=list(row.get("tags", [])),
            )
        )
    return cases


def load_retrieval_cases(path: Path = DATASETS_DIR / "retrieval.jsonl") -> list[RetrievalCase]:
    cases: list[RetrievalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        cases.append(
            RetrievalCase(
                id=row["id"],
                query=row["query"],
                subject=row["subject"],
                gold_pages=[int(p) for p in row["gold_pages"]],
                tags=list(row.get("tags", [])),
            )
        )
    return cases


def _git_short_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return "unknown"


def _snapshot_files(paths: list[Path]) -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in paths if p.exists()}


def _check_and_restore_files(before: dict[Path, str]) -> list[str]:
    changed: list[str] = []
    for path, content in before.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != content:
            changed.append(str(path.relative_to(PROJECT_ROOT)))
            path.write_text(content, encoding="utf-8")
    return changed


def run_skill_selection(target, cases: list[SkillSelectionCase]) -> list[SkillRecord]:
    records: list[SkillRecord] = []
    for case in cases:
        predicted = target.select_skill(case.query)
        records.append(
            SkillRecord(
                case=case,
                predicted=predicted,
                correct=predicted in case.expected_any,
            )
        )
    return records


def run_retrieval(target, cases: list[RetrievalCase]) -> list[RetrievalRecord]:
    records: list[RetrievalRecord] = []
    for idx, case in enumerate(cases, start=1):
        chunks = target.retrieve(case.query, subject=case.subject, k=10)
        rec = evaluate_retrieval_case(case, chunks)
        records.append(rec)
        print(
            f"[retrieval {idx:02d}/{len(cases)}] {case.id} "
            f"hit@5={rec.hit_at_5} rank={rec.first_hit_rank}",
            flush=True,
        )
    return records


def run_e2e(target, cases: list[SkillSelectionCase]) -> tuple[list[E2ERecord], list[str]]:
    e2e_cases = [c for c in cases if "e2e" in c.tags]
    before = _snapshot_files(PROTECTED_DATA_FILES)
    records: list[E2ERecord] = []
    try:
        for idx, case in enumerate(e2e_cases, start=1):
            res = target.run_e2e(case.query)
            records.append(E2ERecord(case=case, result=res))
            print(
                f"[e2e {idx:02d}/{len(e2e_cases)}] {case.id} skill={res.selected_skill} "
                f"latency={res.latency_s:.2f}s llm_calls={res.model_calls} "
                f"tools={len(res.tool_calls)}"
                + (f" ERROR={res.error}" if res.error else ""),
                flush=True,
            )
    finally:
        unexpected_writes = _check_and_restore_files(before)
    return records, unexpected_writes


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_report(
    *,
    target_name: str,
    model_name: str,
    embedding_model_name: str,
    run_date: str,
    commit_sha: str,
    skill_records: list[SkillRecord] | None,
    retrieval_records: list[RetrievalRecord] | None,
    e2e_records: list[E2ERecord] | None,
    unexpected_writes: list[str],
) -> str:
    lines: list[str] = [
        f"# PrimeBuddy 评测报告（{target_name} · {run_date}）",
        "",
        "## 基本信息",
        "",
        f"- **目标系统**：`{target_name}`",
        f"- **主模型**：`{model_name}`",
        f"- **Embedding 模型**：`{embedding_model_name}`",
        f"- **评测日期**：{run_date}",
        f"- **代码提交**：`{commit_sha}`",
        "",
        "## 核心指标汇总",
        "",
        "| 指标 | 数值 | 说明 |",
        "| ---- | ---- | ---- |",
    ]

    skill_metrics = compute_skill_metrics(skill_records) if skill_records is not None else None
    retrieval_metrics = (
        compute_retrieval_metrics(retrieval_records) if retrieval_records is not None else None
    )
    e2e_metrics = compute_e2e_metrics(e2e_records) if e2e_records is not None else None

    if skill_metrics is not None:
        lines.append(
            f"| 技能选择准确率 | {_fmt_pct(skill_metrics['accuracy'])} "
            f"({skill_metrics['correct']}/{skill_metrics['total']}) | 全量技能选择集 |"
        )
        lines.append(
            f"| 口语化审阅子集准确率 | {_fmt_pct(skill_metrics['colloquial_accuracy'])} "
            f"({skill_metrics['colloquial_correct']}/{skill_metrics['colloquial_total']}) | "
            f"8 条口语化审阅题 |"
        )

    if retrieval_metrics is not None:
        lines.append(
            f"| Recall@5 | {_fmt_pct(retrieval_metrics['recall_at_5'])} "
            f"({retrieval_metrics['hits_at_5']}/{retrieval_metrics['total']}) | "
            f"top-5 命中同科目目标页码 |"
        )
        lines.append(
            f"| MRR@10 | {retrieval_metrics['mrr_at_10']:.4f} | "
            f"top-10 首个命中排名倒数均值（Recall@10 = {_fmt_pct(retrieval_metrics['recall_at_10'])}） |"
        )

    if e2e_metrics is not None:
        lines.append(
            f"| 端到端 P50 延迟 | {e2e_metrics['p50_latency_s']:.2f}s | "
            f"{e2e_metrics['total']} 条代表性问答（P95 = {e2e_metrics['p95_latency_s']:.2f}s，"
            f"均值 = {e2e_metrics['avg_latency_s']:.2f}s） |"
        )
        lines.append(
            f"| 每次问答模型调用次数 | {e2e_metrics['avg_model_calls']:.2f} 次 | "
            f"含工具内嵌套 LLM 调用（范围 {e2e_metrics['min_model_calls']}–{e2e_metrics['max_model_calls']}，"
            f"平均工具调用 {e2e_metrics['avg_tool_calls']:.2f} 次） |"
        )

    if skill_records is not None and skill_metrics is not None:
        lines.extend(
            [
                "",
                "## 1. 技能选择评测",
                "",
                "### 分类别统计",
                "",
                "| 类别 | 正确 / 总数 | 准确率 |",
                "| ---- | ----------- | ------ |",
            ]
        )
        for cat, stats in skill_metrics["by_category"].items():
            lines.append(
                f"| `{cat}` | {stats['correct']}/{stats['total']} | {_fmt_pct(stats['accuracy'])} |"
            )

        colloquial = [r for r in skill_records if "colloquial_review" in r.case.tags]
        if colloquial:
            lines.extend(
                [
                    "",
                    "### 口语化审阅子集明细（8 条）",
                    "",
                    "| ID | 问题 | 期望 | 预测 | 结果 |",
                    "| -- | ---- | ---- | ---- | ---- |",
                ]
            )
            for r in colloquial:
                exp = ", ".join(r.case.expected_any)
                mark = "PASS" if r.correct else "FAIL"
                lines.append(
                    f"| `{r.case.id}` | {r.case.query} | `{exp}` | `{r.predicted}` | {mark} |"
                )

        wrong = [r for r in skill_records if not r.correct]
        lines.extend(
            [
                "",
                f"### 错判样本（共 {len(wrong)} 条）",
                "",
                "| ID | 类别 | 问题 | 期望 | 预测 |",
                "| -- | ---- | ---- | ---- | ---- |",
            ]
        )
        for r in wrong:
            exp = ", ".join(r.case.expected_any)
            lines.append(
                f"| `{r.case.id}` | `{r.case.category}` | {r.case.query} | `{exp}` | `{r.predicted}` |"
            )

    if retrieval_records is not None and retrieval_metrics is not None:
        lines.extend(
            [
                "",
                "## 2. 检索评测",
                "",
                "### 分科目统计",
                "",
                "| 科目 | 题数 | Recall@5 | Recall@10 | MRR@10 |",
                "| ---- | ---- | -------- | --------- | ------ |",
            ]
        )
        for subj, stats in retrieval_metrics["by_subject"].items():
            lines.append(
                f"| {subj} | {stats['total']} | {_fmt_pct(stats['recall_at_5'])} "
                f"({stats['hits_at_5']}/{stats['total']}) | "
                f"{_fmt_pct(stats['recall_at_10'])} | {stats['mrr_at_10']:.4f} |"
            )

        missed = [r for r in retrieval_records if not r.hit_at_5]
        lines.extend(
            [
                "",
                f"### Top-5 未命中样本（共 {len(missed)} 条）",
                "",
                "| ID | 科目 | 问题 | 目标页码 | Top-5 召回（科目:页码） | Top-10 命中位次 |",
                "| -- | ---- | ---- | -------- | ----------------------- | --------------- |",
            ]
        )
        for r in missed:
            top5_desc = "; ".join(
                f"{c.subject or '?'}:{c.pages}" for c in r.chunks[:5]
            )
            rank_str = str(r.first_hit_rank) if r.first_hit_rank is not None else "未命中"
            lines.append(
                f"| `{r.case.id}` | {r.case.subject} | {r.case.query} | "
                f"{r.case.gold_pages} | {top5_desc} | {rank_str} |"
            )

    if e2e_records is not None and e2e_metrics is not None:
        lines.extend(
            [
                "",
                "## 3. 端到端延迟与模型调用次数",
                "",
                "### 分类别统计",
                "",
                "| 类别 | 样本数 | P50 延迟 | 平均延迟 | 平均模型调用 | 平均工具调用 |",
                "| ---- | ------ | -------- | -------- | ------------ | ------------ |",
            ]
        )
        for cat, stats in e2e_metrics["by_category"].items():
            lines.append(
                f"| `{cat}` | {stats['total']} | {stats['p50_latency_s']:.2f}s | "
                f"{stats['avg_latency_s']:.2f}s | {stats['avg_model_calls']:.2f} | "
                f"{stats['avg_tool_calls']:.2f} |"
            )

        lines.extend(
            [
                "",
                "### 逐题明细",
                "",
                "| ID | 类别 | 路由技能 | 延迟 | 模型调用 | 工具调用 | 异常 |",
                "| -- | ---- | -------- | ---- | -------- | -------- | ---- |",
            ]
        )
        for r in e2e_records:
            tools_str = ", ".join(r.result.tool_calls) if r.result.tool_calls else "-"
            err_str = r.result.error or "-"
            lines.append(
                f"| `{r.case.id}` | `{r.case.category}` | `{r.result.selected_skill}` | "
                f"{r.result.latency_s:.2f}s | {r.result.model_calls} | `{tools_str}` | {err_str} |"
            )

        if unexpected_writes:
            lines.extend(
                [
                    "",
                    f"> **数据副作用警告**：端到端测试期间检测到以下业务数据文件被意外写入（已自动恢复）：`{', '.join(unexpected_writes)}`",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "- **数据副作用检查**：通过（`mistake_records.csv` 与 `weekly_reports.json` 均未被写入）。",
                ]
            )

    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PrimeBuddy evaluation suites.")
    parser.add_argument("--target", default="v1", help="Target system name (e.g. v1, v2).")
    parser.add_argument(
        "--suite",
        default="all",
        choices=["all", "skill_selection", "retrieval", "e2e"],
        help="Evaluation suite to run.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Custom report output path.")
    parser.add_argument("--no-save", action="store_true", help="Print report without writing file.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = load_target(args.target)
    run_date = date.today().isoformat()

    skill_cases = load_skill_cases()
    retrieval_cases = load_retrieval_cases()

    skill_records: list[SkillRecord] | None = None
    retrieval_records: list[RetrievalRecord] | None = None
    e2e_records: list[E2ERecord] | None = None
    unexpected_writes: list[str] = []

    if args.suite in ("all", "skill_selection"):
        skill_records = run_skill_selection(target, skill_cases)
        sm = compute_skill_metrics(skill_records)
        print(
            f"[skill_selection] accuracy={_fmt_pct(sm['accuracy'])} "
            f"({sm['correct']}/{sm['total']}), "
            f"colloquial={sm['colloquial_correct']}/{sm['colloquial_total']}",
            flush=True,
        )

    if args.suite in ("all", "retrieval"):
        retrieval_records = run_retrieval(target, retrieval_cases)
        rm = compute_retrieval_metrics(retrieval_records)
        print(
            f"[retrieval] Recall@5={_fmt_pct(rm['recall_at_5'])}, "
            f"MRR@10={rm['mrr_at_10']:.4f}",
            flush=True,
        )

    if args.suite in ("all", "e2e"):
        e2e_records, unexpected_writes = run_e2e(target, skill_cases)
        em = compute_e2e_metrics(e2e_records)
        print(
            f"[e2e] P50={em['p50_latency_s']:.2f}s, "
            f"avg_model_calls={em['avg_model_calls']:.2f}, "
            f"unexpected_writes={unexpected_writes}",
            flush=True,
        )

    report = render_report(
        target_name=target.name,
        model_name=target.model_name,
        embedding_model_name=target.embedding_model_name,
        run_date=run_date,
        commit_sha=_git_short_sha(),
        skill_records=skill_records,
        retrieval_records=retrieval_records,
        e2e_records=e2e_records,
        unexpected_writes=unexpected_writes,
    )

    if args.no_save:
        print(report)
    else:
        out_path = args.output or (REPORTS_DIR / f"{run_date}-{target.name}.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"Report saved to {out_path}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
