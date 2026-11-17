import csv
import json
from langchain_core.tools import tool
from utils.logger_handler import logger
from utils.path_tool import get_abs_path

USER_PROFILE_PATH = "data/study/user_profile.json"
LEARNING_RECORDS_PATH = "data/study/learning_records.csv"
DEMO_USER_ID = "demo_user"


def normalize_demo_user_id(user_id: str = DEMO_USER_ID) -> str:
    if user_id != DEMO_USER_ID:
        logger.warning(f"[normalize_demo_user_id]演示模式统一使用{DEMO_USER_ID}，忽略传入用户：{user_id}")
    return DEMO_USER_ID


def read_user_profile(user_id: str = DEMO_USER_ID) -> dict:
    user_id = normalize_demo_user_id(user_id)
    profile_path = get_abs_path(USER_PROFILE_PATH)
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    if profile.get("user_id") != user_id:
        logger.warning(f"[get_user_profile]未找到用户：{user_id}，返回默认演示用户画像")

    return profile


def read_learning_records(user_id: str = DEMO_USER_ID, start_date: str = "", end_date: str = "") -> list[dict]:
    user_id = normalize_demo_user_id(user_id)
    records_path = get_abs_path(LEARNING_RECORDS_PATH)
    results = []

    with open(records_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("user_id") != user_id:
                continue
            if start_date and row.get("date", "") < start_date:
                continue
            if end_date and row.get("date", "") > end_date:
                continue
            results.append(row)

    if not results:
        logger.warning(f"[get_learning_records]未检索到用户：{user_id}在{start_date}到{end_date}的学习记录")

    return results


def to_json_text(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@tool(description="获取指定用户的学习画像，以JSON字符串形式返回。")
def get_user_profile(user_id: str = DEMO_USER_ID) -> str:
    return to_json_text(read_user_profile(user_id))


@tool(description="获取指定用户在指定日期范围内的学习记录。日期格式为YYYY-MM-DD；如果起止日期为空字符串，则不限制该边界。")
def get_learning_records(user_id: str = DEMO_USER_ID, start_date: str = "", end_date: str = "") -> str:
    return to_json_text(read_learning_records(user_id, start_date, end_date))
