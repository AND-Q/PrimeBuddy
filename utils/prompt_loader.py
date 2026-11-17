from utils.config_handler import prompts_conf
from utils.path_tool import get_abs_path
from utils.logger_handler import logger


def _load_prompt(config_key: str, label: str) -> str:
    try:
        prompt_path = get_abs_path(prompts_conf[config_key])
    except KeyError as e:
        logger.error(f"[{label}]在yaml配置项中没有{config_key}配置项")
        raise e

    try:
        return open(prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[{label}]解析提示词出错，{str(e)}")
        raise e


def load_system_prompts():
    return _load_prompt("main_prompt_path", "load_system_prompts")


def load_rag_prompts():
    return _load_prompt("rag_summarize_prompt_path", "load_rag_prompts")


def load_report_prompts():
    return _load_prompt("report_prompt_path", "load_report_prompts")


def load_supervisor_prompts():
    return _load_prompt("supervisor_prompt_path", "load_supervisor_prompts")


def load_tutor_prompts():
    return _load_prompt("tutor_prompt_path", "load_tutor_prompts")


def load_planner_prompts():
    return _load_prompt("planner_prompt_path", "load_planner_prompts")


def load_mistake_prompts():
    return _load_prompt("mistake_prompt_path", "load_mistake_prompts")


def load_study_report_prompts():
    return _load_prompt("study_report_prompt_path", "load_study_report_prompts")


if __name__ == '__main__':
    print(load_report_prompts())
