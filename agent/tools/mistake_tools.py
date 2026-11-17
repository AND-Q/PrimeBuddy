import csv
import json
from collections import Counter
from datetime import date
from langchain_core.tools import tool
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
from agent.tools.record_tools import DEMO_USER_ID, normalize_demo_user_id

MISTAKE_RECORDS_PATH = "data/study/mistake_records.csv"
MISTAKE_FIELDS = [
    "id",
    "date",
    "user_id",
    "subject",
    "chapter",
    "question",
    "user_answer",
    "correct_answer",
    "error_reason",
    "knowledge_point",
    "status",
]


def read_mistake_records(user_id: str = DEMO_USER_ID, subject: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
    user_id = normalize_demo_user_id(user_id)
    records_path = get_abs_path(MISTAKE_RECORDS_PATH)
    results = []

    with open(records_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("user_id") != user_id:
                continue
            if subject and row.get("subject") != subject:
                continue
            if start_date and row.get("date", "") < start_date:
                continue
            if end_date and row.get("date", "") > end_date:
                continue
            results.append(row)

    if not results:
        logger.warning(f"[query_mistake_records]未检索到用户：{user_id}的错题记录")

    return results


def next_mistake_id(rows: list[dict]) -> str:
    max_id = 0
    for row in rows:
        raw_id = row.get("id", "").replace("M", "")
        if raw_id.isdigit():
            max_id = max(max_id, int(raw_id))
    return f"M{max_id + 1:03d}"


def to_json_text(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@tool(description="查询指定用户的错题记录。subject为空字符串时返回全部科目；日期格式为YYYY-MM-DD，起止日期为空字符串时不限制该边界。")
def query_mistake_records(user_id: str = DEMO_USER_ID, subject: str = "", start_date: str = "", end_date: str = "") -> str:
    return to_json_text(read_mistake_records(user_id, subject, start_date, end_date))


@tool(description="总结指定用户的错题情况，返回错题数量、科目分布、知识点分布、错因分布和待处理错题。period暂支持all或日期范围文字说明。")
def summarize_mistakes(user_id: str = DEMO_USER_ID, period: str = "all") -> str:
    user_id = normalize_demo_user_id(user_id)
    records = read_mistake_records(user_id)
    subject_counter = Counter(row.get("subject", "未知") for row in records)
    knowledge_counter = Counter(row.get("knowledge_point", "未知") for row in records)
    reason_counter = Counter(row.get("error_reason", "未知") for row in records)
    pending = [row for row in records if row.get("status") != "已复习"]

    summary = {
        "user_id": user_id,
        "period": period,
        "total": len(records),
        "subject_distribution": dict(subject_counter),
        "knowledge_point_distribution": dict(knowledge_counter),
        "error_reason_distribution": dict(reason_counter),
        "pending_review_count": len(pending),
        "pending_review_items": pending,
    }
    return to_json_text(summary)


@tool(description="追加保存一条错题记录，并返回保存后的错题ID。只有用户明确要求保存时，confirm_save才应传True；否则不要写入文件。")
def save_mistake_record(
        subject: str,
        chapter: str,
        question: str,
        user_answer: str,
        correct_answer: str,
        error_reason: str,
        knowledge_point: str,
        user_id: str = DEMO_USER_ID,
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

    user_id = normalize_demo_user_id(user_id)
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
