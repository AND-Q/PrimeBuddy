from dataclasses import dataclass
from utils.logger_handler import logger
from agent.tools.record_tools import DEMO_USER_ID


@dataclass
class RouteResult:
    # 保存路由目标和命中原因，便于日志记录与后续调试。
    route: str
    reason: str


class StudyCopilotSupervisor:
    # 统一管理各类学习专家 Agent，并根据用户问题分发请求。
    def __init__(self):
        self.agents = {}

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

    @staticmethod
    def has_any_keyword(query: str, keywords: list[str]) -> bool:
        return any(keyword in query for keyword in keywords)

    def get_agent(self, route: str):
        if route in self.agents:
            return self.agents[route]

        if route == "tutor":
            from agent.specialists.tutor_agent import TutorAgent
            self.agents[route] = TutorAgent()
        elif route == "planner":
            from agent.specialists.planner_agent import PlannerAgent
            self.agents[route] = PlannerAgent()
        elif route == "mistake":
            from agent.specialists.mistake_agent import MistakeAgent
            self.agents[route] = MistakeAgent()
        elif route == "report":
            from agent.specialists.report_agent import ReportAgent
            self.agents[route] = ReportAgent()
        else:
            return None

        return self.agents[route]

    def general_response(self) -> str:
        return """我是 PrimeBuddy，一个面向学习规划与诊断的多 Agent 智能学习伙伴。当前第一阶段优先支持 408 考研学习闭环。

我可以帮你：

1. 解答 408 知识点，并总结常见考法和易错点；
2. 根据目标、剩余时间和薄弱科目制定学习计划；
3. 分析错题原因，给出复习动作；
4. 根据学习记录和错题记录生成学习周报。

你可以这样问我：

- 请讲一下操作系统中的虚拟内存，并说明 408 常见考法。
- 我还有 8 周考 408，每天 3 小时，帮我制定下周计划。
- 这道 TCP 拥塞控制题我错了，帮我分析原因。
- 请生成我的本周学习报告，指出主要问题和下周重点。
"""

    def execute(self, query: str, user_id: str = DEMO_USER_ID) -> str:
        route_result = self.route(query)
        logger.info(f"[StudyCopilotSupervisor]路由到：{route_result.route}，原因：{route_result.reason}")

        agent = self.get_agent(route_result.route)
        if agent is None:
            return self.general_response()

        return agent.execute(query, user_id=user_id)

    def execute_stream(self, query: str, user_id: str = DEMO_USER_ID):
        route_result = self.route(query)
        logger.info(f"[StudyCopilotSupervisor]路由到：{route_result.route}，原因：{route_result.reason}")

        agent = self.get_agent(route_result.route)
        if agent is None:
            yield self.general_response()
            return

        # 保持流式输出能力，由具体专家 Agent 逐段返回结果。
        yield from agent.execute_stream(query, user_id=user_id)


if __name__ == '__main__':
    supervisor = StudyCopilotSupervisor()
    print(supervisor.route("请生成我的本周学习报告").route)
