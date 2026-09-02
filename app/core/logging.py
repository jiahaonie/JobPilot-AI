"""与业务代码分离的日志配置。"""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """为本地开发配置行为可预测的默认日志器。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
