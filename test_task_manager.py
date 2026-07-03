import json
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

# Импортируем все нужные функции из task_manager
from task_manager import (
    BACKUP_FILE,
    TASKS_FILE,
    add_task,
    append_task_to_file,
    check_overdue_tasks,
    delete_task,
    edit_task_text,
    get_current_datetime,
    load_tasks_from_file,
    parse_target,
    renumber_ids,
    rewrite_all_tasks_to_file,
    sort_by_priority,
    update_status,
)


class TestTaskManager(unittest.TestCase):
    def setUp(self):
        """Создаём чистый список задач перед каждым тестом"""
        self.tasks = []

    def tearDown(self):
        """Удаляем временные файлы после тестов (если создавались)"""
        for filename in [TASKS_FILE, BACKUP_FILE]:
            if os.path.exists(filename):
                os.remove(filename)

    # ========== ТЕСТЫ ДЛЯ parse_target ==========
    def test_parse_target_digit(self):
        self.assertEqual(parse_target("123"), 123)
        self.assertEqual(parse_target("0"), 0)

    def test_parse_target_text(self):
        self.assertEqual(parse_target("hello"), "hello")
        self.assertEqual(parse_target("123abc"), "123abc")

    # ========== ТЕСТЫ ДЛЯ get_current_datetime ==========
    def test_get_current_datetime_format(self):
        result = get_current_datetime()
        # Проверяем формат ГГГГ-ММ-ДД ЧЧ:ММ:СС
        self.assertRegex(result, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    # ========== ТЕСТЫ ДЛЯ renumber_ids ==========
    def test_renumber_ids(self):
        self.tasks = [
            {"id": 5, "text": "A"},
            {"id": 10, "text": "B"},
            {"id": 1, "text": "C"},
        ]
        renumber_ids(self.tasks)
        self.assertEqual(self.tasks[0]["id"], 1)
        self.assertEqual(self.tasks[1]["id"], 2)
        self.assertEqual(self.tasks[2]["id"], 3)

    # ========== ТЕСТЫ ДЛЯ sort_by_priority ==========
    def test_sort_by_priority(self):
        self.tasks = [
            {"id": 1, "text": "Low", "priority": "low"},
            {"id": 2, "text": "High", "priority": "high"},
            {"id": 3, "text": "Medium", "priority": "medium"},
            {"id": 4, "text": "No priority"},  # без priority
        ]
        sorted_tasks = sort_by_priority(self.tasks)
        # high → medium → low → без priority
        self.assertEqual(sorted_tasks[0]["text"], "High")
        self.assertEqual(sorted_tasks[1]["text"], "Medium")
        self.assertEqual(sorted_tasks[2]["text"], "Low")
        # задачи без priority должны быть в конце (сортируются как medium - 2)

    # ========== ТЕСТЫ ДЛЯ add_task ==========
    def test_add_task_success(self):
        result = add_task(self.tasks, "Купить молоко", "high", None)
        self.assertTrue(result[0])
        self.assertEqual(result[1], 1)
        self.assertEqual(len(self.tasks), 1)
        self.assertEqual(self.tasks[0]["text"], "Купить молоко")
        self.assertEqual(self.tasks[0]["priority"], "high")
        self.assertEqual(self.tasks[0]["status"], "pending")

    def test_add_task_with_deadline(self):
        result = add_task(self.tasks, "Сдать проект", "medium", "2025-12-31")
        self.assertTrue(result[0])
        self.assertEqual(self.tasks[0]["deadline"], "2025-12-31")

    def test_add_task_empty_text(self):
        result = add_task(self.tasks, "", "medium", None)
        self.assertFalse(result[0])
        self.assertEqual(len(self.tasks), 0)

    def test_add_task_numeric_text_allowed(self):
        # ВАЖНО: по вашей логике, текст-число запрещён
        result = add_task(self.tasks, "123", "low", None)
        self.assertFalse(result[0])
        self.assertEqual(len(self.tasks), 0)

    def test_add_task_invalid_priority(self):
        result = add_task(self.tasks, "Тест", "invalid", None)
        # Должен установить medium по умолчанию
        self.assertTrue(result[0])
        self.assertEqual(self.tasks[0]["priority"], "medium")

    # ========== ТЕСТЫ ДЛЯ delete_task ==========
    def test_delete_task_by_id(self):
        add_task(self.tasks, "Задача 1", "medium", None)
        add_task(self.tasks, "Задача 2", "medium", None)
        success, msg = delete_task(self.tasks, 1)
        self.assertTrue(success)
        self.assertEqual(len(self.tasks), 1)
        self.assertEqual(self.tasks[0]["text"], "Задача 2")
        self.assertEqual(self.tasks[0]["id"], 1)  # ID должен сдвинуться
        # тест падает потому что id сдвигается после show_tasks а не после удаления.

    def test_delete_task_by_text(self):
        add_task(self.tasks, "Купить хлеб", "medium", None)
        add_task(self.tasks, "Купить молоко", "medium", None)
        success, msg = delete_task(self.tasks, "Купить хлеб")
        self.assertTrue(success)
        self.assertEqual(len(self.tasks), 1)
        self.assertEqual(self.tasks[0]["text"], "Купить молоко")

    def test_delete_task_not_found(self):
        add_task(self.tasks, "Задача 1", "medium", None)
        success, msg = delete_task(self.tasks, 99)
        self.assertFalse(success)
        self.assertEqual(len(self.tasks), 1)

    # ========== ТЕСТЫ ДЛЯ update_status ==========
    def test_update_status_success(self):
        add_task(self.tasks, "Задача 1", "medium", None)
        success, msg = update_status(self.tasks, 1, "done")
        self.assertTrue(success)
        self.assertEqual(self.tasks[0]["status"], "done")

    def test_update_status_invalid_status(self):
        add_task(self.tasks, "Задача 1", "medium", None)
        success, msg = update_status(self.tasks, 1, "invalid")
        self.assertFalse(success)
        self.assertEqual(self.tasks[0]["status"], "pending")  # не изменился

    def test_update_status_task_not_found(self):
        success, msg = update_status(self.tasks, 99, "done")
        self.assertFalse(success)

    # ========== ТЕСТЫ ДЛЯ edit_task_text ==========
    def test_edit_task_text_success(self):
        add_task(self.tasks, "Старый текст", "medium", None)
        old_created = self.tasks[0]["created"]

        # Небольшая задержка, чтобы дата создания точно изменилась
        import time

        time.sleep(1)

        result = edit_task_text(self.tasks, 1, "Новый текст")
        self.assertTrue(result[0])
        self.assertEqual(self.tasks[0]["text"], "Новый текст")
        self.assertNotEqual(self.tasks[0]["created"], old_created)

    def test_edit_task_text_empty_new_text(self):
        add_task(self.tasks, "Задача", "medium", None)
        result = edit_task_text(self.tasks, 1, "")
        self.assertFalse(result[0])
        self.assertEqual(self.tasks[0]["text"], "Задача")  # не изменился

    def test_edit_task_text_numeric_forbidden(self):
        add_task(self.tasks, "Задача", "medium", None)
        result = edit_task_text(self.tasks, 1, "123")
        self.assertFalse(result[0])

    # ========== ТЕСТЫ ДЛЯ check_overdue_tasks ==========
    def test_check_overdue_tasks(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        add_task(self.tasks, "Просрочена", "high", yesterday)
        add_task(self.tasks, "Не просрочена", "high", tomorrow)
        add_task(self.tasks, "Без дедлайна", "medium", None)

        check_overdue_tasks(self.tasks)

        self.assertEqual(self.tasks[0]["status"], "overdue")
        self.assertEqual(self.tasks[1]["status"], "pending")
        self.assertEqual(self.tasks[2]["status"], "pending")

    def test_check_overdue_tasks_done_not_overdue(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        add_task(self.tasks, "Выполненная просрочка", "high", yesterday)
        update_status(self.tasks, 1, "done")

        check_overdue_tasks(self.tasks)

        # Уже done — не меняем на overdue
        self.assertEqual(self.tasks[0]["status"], "done")

    # ========== ТЕСТЫ ДЛЯ ФАЙЛОВЫХ ОПЕРАЦИЙ (с временной папкой) ==========
    @patch("task_manager.TASKS_FILE", "test_temp_tasks.jsonl")
    @patch("task_manager.BACKUP_FILE", "test_temp_tasks.jsonl.bak")
    def test_append_task_to_file(self):
        task = {"id": 1, "text": "Тест", "status": "pending"}
        append_task_to_file(task)

        with open("test_temp_tasks.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["text"], "Тест")

        # cleanup
        os.remove("test_temp_tasks.jsonl")

    @patch("task_manager.TASKS_FILE", "test_temp_rewrite.jsonl")
    @patch("task_manager.BACKUP_FILE", "test_temp_rewrite.jsonl.bak")
    def test_rewrite_all_tasks_to_file(self):
        tasks = [
            {"id": 1, "text": "A", "status": "pending"},
            {"id": 2, "text": "B", "status": "done"},
        ]
        rewrite_all_tasks_to_file(tasks)

        with open("test_temp_rewrite.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 2)

        # cleanup
        os.remove("test_temp_rewrite.jsonl")
        if os.path.exists("test_temp_rewrite.jsonl.bak"):
            os.remove("test_temp_rewrite.jsonl.bak")

    @patch("task_manager.TASKS_FILE", "test_temp_load.jsonl")
    def test_load_tasks_from_file(self):
        # Создаём тестовый файл
        tasks_data = [
            {"id": 1, "text": "A", "status": "pending"},
            {"id": 5, "text": "B", "status": "done"},
        ]
        with open("test_temp_load.jsonl", "w", encoding="utf-8") as f:
            for task in tasks_data:
                f.write(json.dumps(task, ensure_ascii=False) + "\n")

        # Временно подменяем TASKS_FILE
        with patch("task_manager.TASKS_FILE", "test_temp_load.jsonl"):
            loaded = load_tasks_from_file()

        self.assertEqual(len(loaded), 2)
        # ID должны быть перенумерованы
        self.assertEqual(loaded[0]["id"], 1)
        self.assertEqual(loaded[1]["id"], 2)

        # cleanup
        os.remove("test_temp_load.jsonl")


if __name__ == "__main__":
    unittest.main()

    # python -m unittest
