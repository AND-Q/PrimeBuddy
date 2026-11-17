import json
from collections import Counter
from datetime import date, timedelta
from langchain_core.tools import tool
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
from agent.tools.record_tools import DEMO_USER_ID, normalize_demo_user_id, read_user_profile, read_learning_records, to_json_text
from agent.tools.mistake_tools import read_mistake_records

WEEKLY_REPORTS_PATH = "data/study/weekly_reports.json"


def week_range_for(day: date) -> tuple[str, str]:
    week_start = day - timedelta(days=day.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start.isoformat(), week_end.isoformat()


def resolve_report_week(today: date | None = None, user_id: str = DEMO_USER_ID) -> tuple[str, str]:
    today = today or date.today()
    user_id = normalize_demo_user_id(user_id)
    current_start, current_end = week_range_for(today)

    current_learning_records = read_learning_records(user_id, current_start, current_end)
    current_mistake_records = read_mistake_records(user_id, "", current_start, current_end)
    if current_learning_records or current_mistake_records:
        return current_start, current_end

    all_dates = []
    for row in read_learning_records(user_id):
        if row.get("date"):
            all_dates.append(row["date"])
    for row in read_mistake_records(user_id):
        if row.get("date"):
            all_dates.append(row["date"])

    if not all_dates:
        return current_start, current_end

    latest_date = date.fromisoformat(max(all_dates))
    fallback_start, fallback_end = week_range_for(latest_date)
    logger.info(f"[current_week_range]当前自然周无演示数据，回退到最近有数据周：{fallback_start}到{fallback_end}")
    return fallback_start, fallback_end


def current_week_range() -> tuple[str, str]:
    return resolve_report_week()


def summarize_learning_records(records: list[dict]) -> dict:
    subject_minutes = Counter()
    task_counter = Counter()
    completed_count = 0

    for row in records:
        subject = row.get("subject", "未知")
        task_type = row.get("task_type", "未知")
        try:
            minutes = int(row.get("duration_minutes", 0))
        except ValueError:
            minutes = 0

        subject_minutes[subject] += minutes
        task_counter[task_type] += 1
        if row.get("completed") == "true":
            completed_count += 1

    return {
        "record_count": len(records),
        "total_minutes": sum(subject_minutes.values()),
        "subject_minutes": dict(subject_minutes),
        "task_type_distribution": dict(task_counter),
        "completed_count": completed_count,
        "unfinished_count": len(records) - completed_count,
    }


def summarize_mistake_records(records: list[dict]) -> dict:
    return {
        "mistake_count": len(records),
        "subject_distribution": dict(Counter(row.get("subject", "未知") for row in records)),
        "knowledge_point_distribution": dict(Counter(row.get("knowledge_point", "未知") for row in records)),
        "error_reason_distribution": dict(Counter(row.get("error_reason", "未知") for row in records)),
        "pending_review_items": [row for row in records if row.get("status") != "已复习"],
    }


def split_list_field(value: str) -> list[str]:
    normalized = value.replace(";", "；")
    return [item.strip() for item in normalized.split("；") if item.strip()]


@tool(description="获取当前自然周的起止日期，返回YYYY-MM-DD格式的week_start和week_end。")
def get_current_week_range() -> str:
    week_start, week_end = current_week_range()
    return to_json_text({"week_start": week_start, "week_end": week_end})


@tool(description="聚合指定用户在指定周内的周报输入数据，包括用户画像、学习记录摘要、错题摘要和原始记录。日期格式为YYYY-MM-DD。")
def get_weekly_report_inputs(user_id: str = DEMO_USER_ID, week_start: str = "", week_end: str = "") -> str:
    user_id = normalize_demo_user_id(user_id)
    if not week_start or not week_end:
        week_start, week_end = current_week_range()

    profile = read_user_profile(user_id)
    learning_records = read_learning_records(user_id, week_start, week_end)
    mistake_records = read_mistake_records(user_id, "", week_start, week_end)

    inputs = {
        "user_profile": profile,
        "week_start": week_start,
        "week_end": week_end,
        "learning_summary": summarize_learning_records(learning_records),
        "mistake_summary": summarize_mistake_records(mistake_records),
        "learning_records": learning_records,
        "mistake_records": mistake_records,
    }
    return to_json_text(inputs)


@tool(description="保存一份学习周报到weekly_reports.json，返回保存结果。只有用户明确要求保存时，confirm_save才应传True；strengths、weaknesses、recommended_next_week_plan和risk_flags可使用中文或英文分号分隔多项。")
def save_weekly_report(
        summary: str,
        strengths: str,
        weaknesses: str,
        recommended_next_week_plan: str,
        risk_flags: str,
        user_id: str = DEMO_USER_ID,
        week_start: str = "",
        week_end: str = "",
        confirm_save: bool = False,
) -> str:
    if not confirm_save:
        return to_json_text(
            {
                "saved": False,
                "reason": "需要用户明确确认保存后才能写入学习周报。",
            }
        )

    user_id = normalize_demo_user_id(user_id)
    if not week_start or not week_end:
        week_start, week_end = current_week_range()

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
