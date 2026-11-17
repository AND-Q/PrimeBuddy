import os
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
MISTAKES_PATH = PROJECT_ROOT / "data" / "study" / "mistake_records.csv"
REPORTS_PATH = PROJECT_ROOT / "data" / "study" / "weekly_reports.json"

PROMPTS = [
    "请用 408 考研的角度讲一下操作系统中的虚拟内存，并说明常见考点。",
    "我还有 8 周考 408，每天能学 3 小时，操作系统和计网比较弱，帮我制定下周计划。",
    "我做错了一道题：TCP 拥塞控制中慢开始和拥塞避免的区别是什么？我把阈值变化理解错了，帮我分析原因并给复习建议。",
    "请生成我的本周学习报告，指出主要问题和下周重点。",
]


def snapshot_data_files() -> tuple[str, str]:
    return (
        MISTAKES_PATH.read_text(encoding="utf-8"),
        REPORTS_PATH.read_text(encoding="utf-8"),
    )


def main() -> int:
    before = snapshot_data_files()
    app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=300).run()

    assert app.title[0].value == "PrimeBuddy"
    assert "408 考研学习" in app.caption[0].value
    assert len(app.chat_message) == 1
    assert "PrimeBuddy" in app.chat_message[0].markdown[0].value

    for prompt in PROMPTS:
        app.chat_input[0].set_value(prompt).run()
        assert len(app.chat_message) >= 3, prompt
        latest = app.chat_message[-1].markdown[0].value.strip()
        assert latest, prompt
        assert "扫地机器人" not in latest, prompt

    after = snapshot_data_files()
    assert before == after, "默认 golden prompts 不应写入错题或周报数据"
    print("streamlit ui golden prompt smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
