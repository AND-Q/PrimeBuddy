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

    def test_save_normalizes_default_user(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            records_path = Path(tmpdir) / "mistake_records.csv"
            self.write_records_file(records_path)

            with patch.object(mistake_tools, "get_abs_path", return_value=str(records_path)):
                result = mistake_tools.save_mistake_record.invoke(
                    {
                        "user_id": "default_user",
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
            self.assertEqual(rows[-1]["user_id"], "demo_user")


if __name__ == "__main__":
    unittest.main()
