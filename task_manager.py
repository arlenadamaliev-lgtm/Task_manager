"""
Менеджер задач
основной функционал:
+ Добавить задачу текст дата создания автоматически -, чек одинаковых задач с предложением перезаписать
+ Вывод всех задач с их статусом - приоритетом
+ Удалить задачу (по тексту или ID)
+ Отметить выполненной (по номеру или ID)
+ Отметить задачу проваленной (по номеру или ID)
+ Logging
- Сохранить в файл (все задачи)
- Загрузить из файла (при запуске или по команде)
+ Приоритеты (высокий/средний/низкий) + сортировка при показе
+ Дедлайн (дата, до которой нужно выполнить), проверка просроченных задач
+ Редактирование текста задачи (без удаления и создания новой)
"""

import json
import os
import shutil
from datetime import datetime

from my_logger import log_action, log_error

TASKS_FILE = "tasks_log.jsonl"
BACKUP_FILE = "tasks_log.jsonl.bak"


def renumber_ids(task_list):
    """Перенумеровывает ID задач от 1 до N (для использования после удаления)."""
    for index, task in enumerate(task_list, start=1):
        task["id"] = index


def parse_target(target_str):
    """Преобразует строку в int, если это число, иначе возвращает как есть."""
    return int(target_str) if target_str.isdigit() else target_str


def get_valid_deadline():
    """Запрашивает дедлайн, проверяет формат, возвращает строку или None."""
    deadline = input("Введите дедлайн (ГГГГ-ММ-ДД) или Enter без даты: ").strip()
    if not deadline:
        return None
    try:
        datetime.strptime(deadline, "%Y-%m-%d")
        return deadline
    except ValueError:
        print("❌ Неверный формат даты. Дедлайн не установлен.")
        return None


def get_valid_priority():
    """Запрашивает приоритет, возвращает 'medium' по умолчанию."""
    print("Доступные приоритеты: high (🔴), medium (🟡), low (🟢)")
    priority = input("Введите приоритет (Enter — medium): ").strip().lower()
    return priority if priority in ("high", "medium", "low") else "medium"


def load_tasks_from_file():
    """
    Загружает задачи из JSONL-файла.
    Возвращает список задач (пустой, если файла нет или он пуст).
    """
    tasks = []

    if not os.path.exists(TASKS_FILE):
        log_action("FILE_LOAD", "Файл не найден, начинаем с пустого списка")
        return tasks

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:  # пропускаем пустые строки
                    task = json.loads(line)
                    tasks.append(task)

        log_action("FILE_LOAD", f"Загружено {len(tasks)} задач из {TASKS_FILE}")

        # Перенумеровываем ID после загрузки (на случай старых ID)
        renumber_ids(tasks)
        log_action("FILE_LOAD", f"ID перенумерованы: теперь {len(tasks)} задач")

    except json.JSONDecodeError as e:
        log_error("FILE_LOAD", f"Ошибка парсинга JSON на строке {line_num}: {e}")
        print(f"❌ Ошибка чтения файла: {e}")
    except Exception as e:
        log_error("FILE_LOAD", f"Неизвестная ошибка: {e}")
        print(f"❌ Не удалось загрузить файл: {e}")

    return tasks


def append_task_to_file(task):
    """
    Добавляет одну задачу в конец JSONL-файла.
    task: словарь задачи
    """
    mode = "a" if os.path.exists(TASKS_FILE) else "w"
    with open(TASKS_FILE, mode, encoding="utf-8") as f:
        f.write(json.dumps(task, ensure_ascii=False) + "\n")
    log_action("FILE_APPEND", f"Добавлена задача ID: {task.get('id')}")


def rewrite_all_tasks_to_file(task_list):
    """
    Перезаписывает весь файл текущим списком задач.
    Перед перезаписью создаёт резервную копию.
    task_list: список словарей задач
    """
    # Создаём резервную копию, если файл существует
    if os.path.exists(TASKS_FILE):
        shutil.copy2(TASKS_FILE, BACKUP_FILE)
        log_action("FILE_BACKUP", f"Создана копия: {BACKUP_FILE}")

    # Перезаписываем файл
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        for task in task_list:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")

    log_action("FILE_REWRITE", f"Перезаписано {len(task_list)} задач")


def sort_by_priority(task_list):
    """Возвращает новый список задач, отсортированных по приоритету (high → medium → low)."""
    priority_order = {"high": 1, "medium": 2, "low": 3}
    return sorted(
        task_list,
        key=lambda task: priority_order.get(task.get("priority", "medium"), 2),
    )


def get_current_datetime():
    """Возвращает текущую дату и время в формате ГГГГ-ММ-ДД ЧЧ:ММ:СС"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def check_overdue_tasks(task_list):
    """
    Проверяет все задачи: если дедлайн задан и меньше текущей даты,
    а статус не "done", то меняет статус на "overdue".
    """
    today = datetime.now().date()
    for task in task_list:
        if task.get("deadline") and task["status"] != "done":
            deadline_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            if deadline_date < today:
                task["status"] = "overdue"
                log_action(
                    "AUTO_OVERDUE",
                    f"ID: {task['id']}, текст: {task['text']}, дедлайн: {task['deadline']}",
                )


def delete_task(task_list, task_id_or_text):
    """
    Удаляет задачу по ID (int) или точному совпадению текста (str).
    Возвращает:
        - (True, "сообщение") если успех
        - (False, "сообщение") если ошибка
    """
    for index, task in enumerate(task_list):
        if task["id"] == task_id_or_text or task["text"] == task_id_or_text:
            log_action("DELETE_TASK", f"ID: {task['id']}, текст: {task['text']}")
            rewrite_all_tasks_to_file(task_list)
            del task_list[index]
            return True, f"Задача {task['text']} удалена."

    log_error("DELETE_TASK", f"Задача с ID/текстом '{task_id_or_text}' не найдена")
    return False, f"Задача с ID/текстом '{task_id_or_text}' не найдена."


def update_status(task_list, task_id_or_text, new_status):
    """
    Обновляет статус задачи по ID (int) или точному совпадению текста (str).
    new_status: "pending", "done", "overdue"
    Возвращает:
        - (True, "сообщение") если успех
        - (False, "сообщение") если ошибка
    """
    if new_status not in ("pending", "done", "overdue"):
        return (
            False,
            f"Недопустимый статус: {new_status}. Допустимые: pending, done, overdue",
        )

    for task in task_list:
        if task["id"] == task_id_or_text or task["text"] == task_id_or_text:
            old_status = task["status"]
            task["status"] = new_status
            log_action(
                "UPDATE_STATUS",
                f"ID: {task['id']}, текст: {task['text']}, статус: {old_status} → {new_status}",
            )
            rewrite_all_tasks_to_file(task_list)
            return (
                True,
                f"Статус задачи '{task['text']}' изменён с '{old_status}' на '{new_status}'.",
            )
    log_error("UPDATE_STATUS", f"Задача с ID/текстом '{task_id_or_text}' не найдена")
    return False, f"Задача с ID/текстом '{task_id_or_text}' не найдена."


def edit_task_text(task_list, task_id_or_text, new_text):
    """
    Изменяет текст задачи по ID (int) или точному совпадению текста (str).
    При редактировании обновляет дату создания.
    Возвращает:
        - (True, old_text, new_text, "сообщение") если успех
        - (False, "сообщение") если ошибка
    """
    if not new_text or new_text.strip() == "":
        log_error("EDIT_TASK", "Новый текст задачи пуст")
        return False, "Новый текст задачи не может быть пустым."
    if new_text.isdigit():
        log_error("EDIT_TASK", "Новый текст задачи состоит только из цифр")
        return False, "Текст задачи не может быть только числовым."

    for task in task_list:
        if task["id"] == task_id_or_text or task["text"] == task_id_or_text:
            old_text = task["text"]
            task["text"] = new_text.strip()
            task["created"] = get_current_datetime()  # обновляем дату создания
            log_action(
                "EDIT_TASK",
                f"ID: {task['id']}, старый текст: '{old_text}', новый текст: '{new_text.strip()}'",
            )
            rewrite_all_tasks_to_file(task_list)
            return (
                True,
                old_text,
                new_text.strip(),
                f"Текст задачи изменён с '{old_text}' на '{new_text.strip()}' (дата обновлена).",
            )
    log_error("EDIT_TASK", f"Задача с ID/текстом '{task_id_or_text}' не найдена")
    return False, f"Задача с ID/текстом '{task_id_or_text}' не найдена."


def add_task(task_list, text, priority, deadline=None):
    """
    Добавляет новую задачу.
    Возвращает:
        - (True, task_id, "сообщение") если успех
        - (False, "сообщение") если ошибка
    """
    if not text:
        log_error("ADD_TASK", "Текст задачи пуст")
        return False, "Текст задачи не может быть пустым."

    if text.isdigit():
        log_error("ADD_TASK", "Текст задачи является числом")
        return False, "Текст задачи не может быть только числовым."
    if priority not in ("high", "medium", "low"):
        print(f"Недопустимый приоритет: {priority}. Допустимые: high, medium, low")
        priority = "medium"

    task_id = len(task_list) + 1
    task = {
        "id": task_id,
        "text": text,
        "status": "pending",
        "created": get_current_datetime(),
        "priority": priority,
    }

    if deadline:
        task["deadline"] = deadline

    task_list.append(task)
    log_action(
        "ADD_TASK",
        f"ID: {task_id}, текст: {text.strip()}, приоритет: {priority}, дедлайн: {deadline}",
    )
    append_task_to_file(task)
    return True, task_id, f"Задача добавлена: {text} (ID: {task_id})"


def show_tasks(task_list):
    """Показывает все задачи с их статусом"""
    if not task_list:
        print("\n📭 Список задач пуст.")
        return

    check_overdue_tasks(task_list)
    task_list[:] = sort_by_priority(task_list)
    rewrite_all_tasks_to_file(task_list)
    print("Отсортированный по приоритету список задач:")

    for task in task_list:
        status_icon = (
            "✓"
            if task["status"] == "done"
            else ("⚓ " if task["status"] == "overdue" else "◻")
        )

        deadline_info = ""
        if task.get("deadline"):
            deadline_info = f", дедлайн: {task['deadline']}"

        print(
            f"{status_icon} {task['id']}. {task['text']} (создана: {task['created']}) {deadline_info}"
        )
    return


def main():

    tasks = load_tasks_from_file()

    while True:
        print("\n--- МЕНЕДЖЕР ЗАДАЧ ---")
        print("1. Добавить задачу")
        print("2. Показать все задачи")
        print("3. Удалить задачу")
        print("4. Сменить статус (pending/done/overdue)")
        print("5. Изменить текст задачи")
        print("0. Выход")

        choice = input("Выберите действие (0-5): ").strip()

        if choice == "0":
            print("До свидания!")
            break

        elif choice == "1":
            text = input("Введите текст задачи: ").strip()
            deadline = get_valid_deadline()
            priority = get_valid_priority()

            result = add_task(tasks, text, priority, deadline)
            print(f"✅ {result[2]}" if result[0] else f"❌ {result[1]}")  # type: ignore

        elif choice == "2":
            show_tasks(tasks)

        elif choice == "3":
            target = parse_target(
                input("Введите номер или текст задачи для удаления: ").strip()
            )
            success, msg = delete_task(tasks, target)
            print(f"🗑️ {msg}" if success else f"❌ {msg}")

        elif choice == "4":
            target = parse_target(input("Введите номер или текст задачи: ").strip())
            new_status = (
                input("Введите новый статус (pending/done/overdue): ").strip().lower()
            )
            success, msg = update_status(tasks, target, new_status)
            print(f"✅ {msg}" if success else f"❌ {msg}")

        elif choice == "5":
            target = parse_target(
                input("Введите номер или текущий текст задачи: ").strip()
            )
            new_text = input("Введите новый текст задачи: ").strip()
            result = edit_task_text(tasks, target, new_text)
            if result[0]:
                print(f"✅ {result[3]}")  # type: ignore
            else:
                print(f"❌ {result[1]}")

        else:
            print("Ошибка: введите число от 0 до 5.")


if __name__ == "__main__":
    main()
