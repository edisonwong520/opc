"""
OPC unified logger module.

Provides a centralized logging configuration for the OPC backend.
All modules should use this logger instead of creating their own.

Usage:
    from opc_server.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Message")
    logger.error("Error message", exc_info=True)
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with OPC standard configuration.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

    return logger


# Pre-configured loggers for common use
app_logger = get_logger("opc.app")
mission_logger = get_logger("opc.mission")
openclaw_logger = get_logger("opc.openclaw")