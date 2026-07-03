# my_logger.py
import logging

# Настройка логгера
LOG_FILE = "task_manager.log"

# Создаём логгер
logger = logging.getLogger("TaskManager")
logger.setLevel(logging.INFO)

# Если логгер уже настроен (чтобы не дублировать handlers при повторном импорте)
if not logger.handlers:
    # Создаём обработчик для записи в файл
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # Создаём обработчик для вывода в консоль (опционально)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # В консоль только WARNING и выше

    # Формат лога: время - уровень - сообщение
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Добавляем обработчики
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
