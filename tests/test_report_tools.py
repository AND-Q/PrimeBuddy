import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from agent.tools import report_tools


class ReportToolsTest(unittest.TestCase):
    def test_split_list_field_accepts_chinese_and_english_semicolons(self):
        result = report_tools.split_list_field("优势一；优势二; 优势三；  ;")
        self.assertEqual(result, ["优势一", "优势二", "优势三"])

    def test_resolve_report_week_falls_back_to_latest_data_week(self):
        learning_rows = [{"user_id": "demo_user", "date": "2026-05-15"}]

        def fake_learning_records(user_id="demo_user", start_date="", end_date=""):
            return [
                row for row in learning_rows
                if (not start_date or row["date"] >= start_date) and (not end_date or row["date"] <= end_date)
            ]

        with patch.object(report_tools, "read_learning_records", side_effect=fake_learning_records):
            with patch.object(report_tools, "read_mistake_records", return_value=[]):
                self.assertEqual(report_tools.resolve_report_week(date(2026, 5, 18)), ("2026-05-11", "2026-05-17"))

    def test_resolve_report_week_keeps_current_week_when_data_exists(self):
        learning_rows = [{"user_id": "demo_user", "date": "2026-05-18"}]

        def fake_learning_records(user_id="demo_user", start_date="", end_date=""):
            return [
                row for row in learning_rows
                if (not start_date or row["date"] >= start_date) and (not end_date or row["date"] <= end_date)
            ]

        with patch.object(report_tools, "read_learning_records", side_effect=fake_learning_records):
            with patch.object(report_tools, "read_mistake_records", return_value=[]):
                self.assertEqual(report_tools.resolve_report_week(date(2026, 5, 18)), ("2026-05-18", "2026-05-24"))

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

    def test_save_weekly_report_normalizes_default_user(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_path = Path(tmpdir) / "weekly_reports.json"
            reports_path.write_text("[]", encoding="utf-8")

            with patch.object(report_tools, "get_abs_path", return_value=str(reports_path)):
                result = report_tools.save_weekly_report.invoke(
                    {
                        "user_id": "default_user",
                        "week_start": "2026-05-11",
                        "week_end": "2026-05-17",
                        "summary": "本周完成操作系统复习。",
                        "strengths": "坚持完成每日任务",
                        "weaknesses": "计网投入不足",
                        "recommended_next_week_plan": "补计网",
                        "risk_flags": "时间分配不均",
                        "confirm_save": True,
                    }
                )

            payload = json.loads(result)
            reports = json.loads(reports_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["saved"])
            self.assertEqual(reports[0]["user_id"], "demo_user")


if __name__ == "__main__":
    unittest.main()
