# Управление базой данных пользователей

import json
import os
from typing import Optional, Dict
from datetime import datetime
from config import USERS_DB
import logging

logger = logging.getLogger(__name__)


class UserDatabase:
    """Класс для управления базой данных пользователей"""

    def __init__(self, db_path: str = USERS_DB):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Создает файл БД если его нет"""
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            logger.info(f"Создана новая БД: {self.db_path}")

    def _read_db(self) -> Dict:
        """Читает БД из файла"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при чтении БД: {str(e)}")
            return {}

    def _write_db(self, data: Dict):
        """Записывает БД в файл"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при записи БД: {str(e)}")

    def add_user(self, user_id: int, group: str) -> bool:
        """
        Добавляет или обновляет пользователя
        Возвращает True если успешно
        """
        try:
            db = self._read_db()
            user_id_str = str(user_id)

            db[user_id_str] = {
                'group': group,
                'registered': datetime.now().isoformat(),
                'notifications': True
            }

            self._write_db(db)
            logger.info(f"Пользователь {user_id} зарегистрирован с группой {group}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {str(e)}")
            return False

    def get_user_group(self, user_id: int) -> Optional[str]:
        """Возвращает группу пользователя или None если пользователя нет"""
        try:
            db = self._read_db()
            user_data = db.get(str(user_id))

            if user_data:
                return user_data.get('group')
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении группы пользователя: {str(e)}")
            return None

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Возвращает полные данные пользователя"""
        try:
            db = self._read_db()
            return db.get(str(user_id))
        except Exception as e:
            logger.error(f"Ошибка при получении данных пользователя: {str(e)}")
            return None

    def user_exists(self, user_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь"""
        return self.get_user_group(user_id) is not None

    def update_group(self, user_id: int, new_group: str) -> bool:
        """Обновляет группу пользователя"""
        try:
            db = self._read_db()
            user_id_str = str(user_id)

            if user_id_str in db:
                db[user_id_str]['group'] = new_group
                db[user_id_str]['updated'] = datetime.now().isoformat()
                self._write_db(db)
                logger.info(f"Группа пользователя {user_id} обновлена на {new_group}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении группы: {str(e)}")
            return False

    def set_notifications(self, user_id: int, enabled: bool) -> bool:
        """Включает/выключает уведомления"""
        try:
            db = self._read_db()
            user_id_str = str(user_id)

            if user_id_str in db:
                db[user_id_str]['notifications'] = enabled
                self._write_db(db)
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при изменении уведомлений: {str(e)}")
            return False

    def get_all_users(self) -> Dict[int, Dict]:
        """Возвращает всех пользователей"""
        try:
            db = self._read_db()
            return {int(user_id): data for user_id, data in db.items()}
        except Exception as e:
            logger.error(f"Ошибка при получении всех пользователей: {str(e)}")
            return {}

    def get_users_for_notifications(self) -> Dict[int, str]:
        """Возвращает {user_id: group} для пользователей с включенными уведомлениями"""
        try:
            db = self._read_db()
            users = {}
            for user_id_str, data in db.items():
                if data.get('notifications', True):
                    users[int(user_id_str)] = data.get('group')
            return users
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей для уведомлений: {str(e)}")
            return {}

    def delete_user(self, user_id: int) -> bool:
        """Удаляет пользователя из БД"""
        try:
            db = self._read_db()
            user_id_str = str(user_id)

            if user_id_str in db:
                del db[user_id_str]
                self._write_db(db)
                logger.info(f"Пользователь {user_id} удален")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя: {str(e)}")
            return False
