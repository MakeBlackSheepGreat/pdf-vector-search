"""
统一配置管理 - 从 .env 文件和环境变量加载配置

使用方式:
    from config import get_config, load_cli_config
    cfg = get_config()
    cfg, _ = load_cli_config(require_pdf=True)  # CLI 脚本一步到位
"""

import os
import argparse
from pathlib import Path
from dataclasses import dataclass

# 加载 .env 文件（如果存在）
# 优先级: .api_key（密钥专用） → .env（通用配置） → 环境变量 → 默认值
try:
    from dotenv import load_dotenv
    _dir = Path(__file__).parent
    # 先加载 .api_key（密钥专用文件）
    _key_path = _dir / ".api_key"
    if _key_path.exists():
        load_dotenv(_key_path)
    # 再加载 .env（不覆盖已存在的变量，这样 .api_key 优先）
    _env_path = _dir / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
except ImportError:
    pass

# 字段名 → 环境变量名 的映射
_ENV_MAP = {
    "api_key": "SILICONFLOW_API_KEY",
    "api_base": "SILICONFLOW_API_BASE",
    "embedding_model": "EMBEDDING_MODEL",
    "db_path": "CHROMA_DB_PATH",
    "collection_name": "COLLECTION_NAME",
    "pdf_path": "PDF_PATH",
    "chunk_size": "CHUNK_SIZE",
    "chunk_overlap": "CHUNK_OVERLAP",
    "top_k": "TOP_K",
    "output_dir": "OUTPUT_DIR",
}

# CLI 参数名 → Config 字段名 的映射（仅不一致的几项）
_ARG_TO_FIELD = {
    "collection": "collection_name",
    "pdf": "pdf_path",
}


@dataclass
class Config:
    """系统配置"""

    api_key: str = ""
    api_base: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "Qwen/Qwen3-VL-Embedding-8B"
    db_path: str = "./chroma_db"
    collection_name: str = "pdf_collection"
    pdf_path: str = ""
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    output_dir: str = "./output"

    def validate(self, require_pdf: bool = False) -> None:
        """验证配置完整性，失败抛 ValueError"""
        errors = []
        if not self.api_key:
            errors.append(
                "未设置 API Key。请通过以下方式之一设置:\n"
                "  1. .env 文件: SILICONFLOW_API_KEY=sk-xxx\n"
                "  2. 环境变量: export SILICONFLOW_API_KEY=sk-xxx\n"
                "  3. 命令行参数: --api-key sk-xxx"
            )
        if require_pdf:
            if not self.pdf_path:
                errors.append(
                    "未指定 PDF 文件。请通过 --pdf 或 .env 中的 PDF_PATH 设置"
                )
            elif not Path(self.pdf_path).exists():
                errors.append(f"PDF 文件不存在: {self.pdf_path}")
        if errors:
            raise ValueError("\n".join(errors))


def get_config(**overrides) -> Config:
    """
    获取配置，优先级: overrides > .env/环境变量 > dataclass 默认值
    """
    cfg = Config()
    # 用环境变量填充非默认值
    for field_name, env_key in _ENV_MAP.items():
        env_val = os.getenv(env_key)
        if env_val is not None:
            field_type = type(getattr(cfg, field_name))
            setattr(cfg, field_name, field_type(env_val))
    # 手动覆盖
    for key, value in overrides.items():
        if hasattr(cfg, key) and value is not None:
            setattr(cfg, key, value)
    return cfg


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """为 argparse 解析器添加通用参数"""
    parser.add_argument("--api-key", help="硅基流动 API Key")
    parser.add_argument("--api-base", help="API Base URL")
    parser.add_argument("--embedding-model", help="嵌入模型名称")
    parser.add_argument("--db-path", help="ChromaDB 存储路径")
    parser.add_argument("--collection", help="集合名称")
    parser.add_argument("--pdf", help="PDF 文件路径")
    parser.add_argument("--chunk-size", type=int, help="文本分块大小")
    parser.add_argument("--chunk-overlap", type=int, help="文本分块重叠")
    parser.add_argument("--top-k", type=int, help="搜索返回结果数")


def _args_to_overrides(args: argparse.Namespace) -> dict:
    """将 argparse Namespace 转为 overrides dict，自动映射字段名"""
    overrides = {}
    for arg_name, value in vars(args).items():
        if value is None:
            continue
        # 特殊映射，其余与 Config 字段名一致
        cfg_name = _ARG_TO_FIELD.get(arg_name, arg_name)
        if hasattr(Config, cfg_name):
            overrides[cfg_name] = value
    return overrides


def load_cli_config(
    description: str = "",
    require_pdf: bool = False,
    extra_args_fn=None,
) -> tuple:
    """
    CLI 脚本一步到位: 解析参数 → 读取环境变量 → 合并 → 验证

    Args:
        description: argparse 描述
        require_pdf: 是否要求 PDF 路径有效
        extra_args_fn: 可选回调 fn(parser)，添加额外的 argparse 参数

    Returns:
        (Config, argparse.Namespace) 元组，cfg 已验证
    """
    parser = argparse.ArgumentParser(description=description)
    _add_common_args(parser)
    if extra_args_fn:
        extra_args_fn(parser)
    args = parser.parse_args()
    cfg = get_config(**_args_to_overrides(args))
    cfg.validate(require_pdf=require_pdf)
    return cfg, args
