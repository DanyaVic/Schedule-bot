import sqlite3
from typing import Optional, Dict, List
from datetime import datetime
from config import USERS_DB
import logging

logger = logging.getLogger(__name__)


class UserDatabase:
    """Класс для управления БД пользователей на SQLite"""

    def __init__(self, db_path: str = USERS_DB):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Создает таблицы БД если их нет"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Таблица пользователей (используем двойные кавычки для "group")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    "group" TEXT NOT NULL,
                    registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated TIMESTAMP,
                    notifications BOOLEAN DEFAULT 1
                )
            ''')

            conn.commit()
            conn.close()
            logger.info(f"✅ БД инициализирована: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации БД: {str(e)}")

    def add_user(self, user_id: int, group: str) -> bool:
        """Добавляет или обновляет пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, "group", registered, notifications)
                VALUES (?, ?, CURRENT_TIMESTAMP, 1)
            ''', (user_id, group))

            conn.commit()
            conn.close()
            logger.info(f"✅ Пользователь {user_id} зарегистрирован с группой {group}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении пользователя: {str(e)}")
            return False

    def get_user_group(self, user_id: int) -> Optional[str]:
        """Возвращает группу пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT "group" FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()

            return result[0] if result else None
        except Exception as e:
            logger.error(f"❌ Ошибка при получении группы: {str(e)}")
            return None

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Возвращает полные данные пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT user_id, "group", registered, updated, notifications 
                FROM users WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'user_id': result[0],
                    'group': result[1],
                    'registered': result[2],
                    'updated': result[3],
                    'notifications': bool(result[4])
                }
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка при получении данных: {str(e)}")
            return None

    def user_exists(self, user_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь"""
        return self.get_user_group(user_id) is not None

    def update_group(self, user_id: int, new_group: str) -> bool:
        """Обновляет группу пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE users 
                SET "group" = ?, updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (new_group, user_id))

            affected = cursor.rowcount
            conn.commit()
            conn.close()

            if affected > 0:
                logger.info(f"✅ Группа {user_id} → {new_group}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении группы: {str(e)}")
            return False

    def set_notifications(self, user_id: int, enabled: bool) -> bool:
        """Включает/выключает уведомления"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE users 
                SET notifications = ?
                WHERE user_id = ?
            ''', (1 if enabled else 0, user_id))

            affected = cursor.rowcount
            conn.commit()
            conn.close()

            if affected > 0:
                logger.info(f"✅ Уведомления {user_id}: {enabled}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка при изменении уведомлений: {str(e)}")
            return False

    def get_all_users(self) -> Dict[int, Dict]:
        """Возвращает всех пользователей"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT user_id, "group", registered, updated, notifications 
                FROM users
            ''')

            users = {}
            for row in cursor.fetchall():
                users[row[0]] = {
                    'group': row[1],
                    'registered': row[2],
                    'updated': row[3],
                    'notifications': bool(row[4])
                }

            conn.close()
            return users
        except Exception as e:
            logger.error(f"❌ Ошибка при получении пользователей: {str(e)}")
            return {}

    def get_users_for_notifications(self) -> Dict[int, str]:
        """Возвращает {user_id: group} с уведомлениями"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT user_id, "group" FROM users 
                WHERE notifications = 1
            ''')

            users = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            return users
        except Exception as e:
            logger.error(f"❌ Ошибка при получении пользователей: {str(e)}")
            return {}

    def delete_user(self, user_id: int) -> bool:
        """Удаляет пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))

            affected = cursor.rowcount
            conn.commit()
            conn.close()

            if affected > 0:
                logger.info(f"✅ Пользователь {user_id} удален")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении: {str(e)}")
            return False

    def get_users_by_group(self, group: str) -> List[int]:
        """Возвращает user_id для группы"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT user_id FROM users WHERE "group" = ?', (group,))
            users = [row[0] for row in cursor.fetchall()]

            conn.close()
            return users
        except Exception as e:
            logger.error(f"❌ Ошибка при получении пользователей: {str(e)}")
            return []

    def get_stats(self) -> Dict:
        """Возвращает статистику БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM users')
            total = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM users WHERE notifications = 1')
            notif = cursor.fetchone()[0]

            cursor.execute('''
                SELECT "group", COUNT(*) as count 
                FROM users 
                GROUP BY "group" 
                ORDER BY count DESC
            ''')

            groups = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()

            return {
                'total_users': total,
                'users_with_notifications': notif,
                'groups': groups
            }
        except Exception as e:
            logger.error(f"❌ Ошибка статистики: {str(e)}")
            return {}
