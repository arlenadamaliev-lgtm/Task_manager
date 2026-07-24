import logging
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(CURRENT_DIR, "task_manager.log")

logger = logging.getLogger("TaskManager")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def log_action(action, details=""):
    """
    Универсальная функция для логирования действий.
    action: строка с названием действия (например, "ADD_TASK", "DELETE_TASK")
    details: дополнительные детали (текст задачи, ID и т.д.)
    """
    message = f"{action}"
    if details:
        message += f" - {details}"
    logger.info(message)


def log_error(action, error_msg):
    """Логирование ошибок."""
    logger.error(f"{action} - ОШИБКА: {error_msg}")


def log_warning(action, warning_msg):
    """Логирование предупреждений."""
    logger.warning(f"{action} - {warning_msg}")
