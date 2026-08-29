"""Logging setup kept separate from business code."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure a predictable default logger for local development."""

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
