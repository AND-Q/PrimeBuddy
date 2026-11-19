"""
yaml
k: v
"""
try:
    import yaml
except ImportError as e:
    raise ImportError(
        "PyYAML is required to load YAML configuration files. Install it with 'pip install pyyaml'."
    ) from e

from utils.path_tool import get_abs_path


def load_yaml_config(config_path: str, encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.safe_load(f)


def load_rag_config(config_path: str = get_abs_path("config/rag.yml"), encoding: str = "utf-8"):
    return load_yaml_config(config_path, encoding)


def load_chroma_config(config_path: str = get_abs_path("config/chroma.yml"), encoding: str = "utf-8"):
    return load_yaml_config(config_path, encoding)


def load_prompts_config(config_path: str = get_abs_path("config/prompts.yml"), encoding: str = "utf-8"):
    return load_yaml_config(config_path, encoding)


rag_conf = load_rag_config()  # 相当于是接收这个字典
chroma_conf = load_chroma_config()
prompts_conf = load_prompts_config()


if __name__ == '__main__':
    print(rag_conf["chat_model_name"])
