import os
import unittest
from unittest.mock import patch

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

    def test_general_execute_does_not_need_model_credentials(self):
        with patch.dict(os.environ, {"MY_API_KEY": "", "MY_BASE_URL": "", "DASHSCOPE_API_KEY": ""}, clear=False):
            supervisor = StudyCopilotSupervisor()
            response = supervisor.execute("你好")

        self.assertIn("PrimeBuddy", response)

    def test_general_execute_stream_does_not_need_model_credentials(self):
        with patch.dict(os.environ, {"MY_API_KEY": "", "MY_BASE_URL": "", "DASHSCOPE_API_KEY": ""}, clear=False):
            supervisor = StudyCopilotSupervisor()
            chunks = list(supervisor.execute_stream("你好"))

        self.assertTrue(chunks)
        self.assertIn("PrimeBuddy", "".join(chunks))


if __name__ == "__main__":
    unittest.main()
