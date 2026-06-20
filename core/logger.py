# core/logger.py
"""
Centralized structured logging for ShopFloorScheduler.
All modules should import `logger` from this module instead of using print().

Usage:
    from core.logger import logger
    logger.info("Loading data...")
    logger.error("Something went wrong: {}", str(e))
"""
import sys
from loguru import logger

# Remove the default loguru handler
logger.remove()

# --- Console Handler (human-readable, colored) ---
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
    level="DEBUG",
    colorize=True,
)

# --- File Handler (structured, persistent) ---
logger.add(
    "logs/shopfloor_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} | {message}",
    level="INFO",
    rotation="1 day",       # New file every day
    retention="7 days",     # Keep logs for 7 days
    compression="zip",      # Compress old logs
    enqueue=True,           # Thread-safe async writing
)

__all__ = ["logger"]
