import pandas as pd
from typing import Dict, List


class ScheduleParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.groups = []
        self.schedule = {}
        self.df = None

    def parse(self) -> bool:
        try:
            self.df = pd.read_excel('schedules/schedule_merged.xlsx', sheet_name=0, header=None)

            self._find_and_extract_groups()

            if not self.groups:
                return False

            # ✅ ДЕБАГ: Выводим найденные группы и их колонки
            print("📋 Найденные группы:")
            for g in self.groups:
                print(f"  {g['name']} → колонка {g['column']}")

            self._parse_schedule()
            return True

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    def _find_and_extract_groups(self):
        for row_idx in range(0, min(30, len(self.df))):
            row = self.df.iloc[row_idx]
            groups_in_row = []

            for col_idx in range(2, len(row)):
                value = row.iloc[col_idx]
                if pd.notna(value):
                    value_str = str(value).strip()
                    if self._is_group_name(value_str):
                        groups_in_row.append({'name': value_str, 'column': col_idx})

            if len(groups_in_row) >= 2:
                self.groups = groups_in_row
                self.groups_row = row_idx
                break

    def _is_group_name(self, value: str) -> bool:
        if 'ИНФОРМАТИКА' in value.upper() or len(value) < 5:
            return False
        if '-' in value and '(' in value and ')' in value and value[0].isdigit():
            return True
        return False

    def _parse_schedule(self):
        days_ranges = {
            'понедельник': (18, 32),
            'вторник': (33, 47),
            'среда': (48, 62),
            'четверг': (63, 78),
            'пятница': (79, 93),
            'суббота': (94, 108),
        }

        for group_info in self.groups:
            group_name = group_info['name']
            col_idx = group_info['column']

            self.schedule[group_name] = {
                'понедельник': [],
                'вторник': [],
                'среда': [],
                'четверг': [],
                'пятница': [],
                'суббота': [],
                'воскресенье': []
            }

            for day_name, (start_row, end_row) in days_ranges.items():
                lessons_by_time = {}
                last_time = None
                last_lesson = None

                for row_idx in range(start_row, end_row + 1):
                    time_value = self.df.iloc[row_idx, 1]
                    lesson_value = self.df.iloc[row_idx, col_idx]

                    # Если в нашей колонке пусто
                    if pd.isna(lesson_value):
                        pass  # Оставляем lesson_value пустым

                    # Если время пусто - используем последнее
                    if pd.isna(time_value):
                        time_value = last_time

                    # Проверяем: есть ли и время и пара?
                    if pd.notna(time_value) and pd.notna(lesson_value):
                        time_str = str(time_value).strip()
                        lesson_str = str(lesson_value).strip()

                        # Обновляем последнее время если это новое время
                        if self._is_time(time_str):
                            last_time = time_str
                            last_lesson = None

                        # Добавляем пару ТОЛЬКО если это не дубликат последней
                        if (self._is_time(time_str) and
                                lesson_str and
                                lesson_str != 'nan' and
                                len(lesson_str) > 2 and
                                lesson_str != last_lesson):

                            if time_str not in lessons_by_time:
                                lessons_by_time[time_str] = set()

                            lessons_by_time[time_str].add(lesson_str)
                            last_lesson = lesson_str

                # 🔑 Сортируем по времени
                sorted_times = sorted(lessons_by_time.keys(), key=lambda t: self._time_to_minutes(t))

                for time_str in sorted_times:
                    formatted = f"⏰ {time_str}"
                    for lesson in sorted(lessons_by_time[time_str]):
                        formatted += f"\n📚 {lesson}"
                    self.schedule[group_name][day_name].append(formatted)

    def _time_to_minutes(self, time_str: str) -> int:
        """Преобразует '8.30-10.00' в минуты для сортировки"""
        try:
            start_time = time_str.split('-')[0].strip()
            hours, minutes = start_time.split('.')
            return int(hours) * 60 + int(minutes)
        except:
            return 0

    def _is_time(self, value: str) -> bool:
        return '-' in value and len(value) >= 8 and ('.' in value or ':' in value)

    def get_groups(self) -> List[str]:
        return [g['name'] for g in self.groups]

    def get_schedule_for_group(self, group: str) -> Dict:
        return self.schedule.get(group, {})

    def get_schedule_for_day(self, group: str, day: str) -> List[str]:
        return self.schedule.get(group, {}).get(day.lower(), [])

    def format_day_schedule(self, group: str, day: str) -> str:
        day_lower = day.lower()
        day_display = {
            'понедельник': '📍 ПОНЕДЕЛЬНИК',
            'вторник': '📍 ВТОРНИК',
            'среда': '📍 СРЕДА',
            'четверг': '📍 ЧЕТВЕРГ',
            'пятница': '📍 ПЯТНИЦА',
            'суббота': '📍 СУББОТА',
            'воскресенье': '📍 ВОСКРЕСЕНЬЕ'
        }

        lessons = self.get_schedule_for_day(group, day)
        if not lessons:
            return f"{day_display.get(day_lower)}\nНет занятий"

        result = f"{day_display.get(day_lower)}\n"
        for lesson in lessons:
            result += f"\n{lesson}\n"
        return result

    def get_schedule_for_week(self, group: str) -> str:
        days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота']
        result = f"📅 Расписание группы {group} на неделю:\n\n"
        for day in days:
            result += self.format_day_schedule(group, day)
            result += "\n" + "─" * 40 + "\n"
        return result


if __name__ == "__main__":
    parser = ScheduleParser('schedules/schedule.xlsx')
    if parser.parse():
        print(f"✅ Найдено групп: {len(parser.get_groups())}")
        first_group = parser.get_groups()[0]
        print(parser.get_schedule_for_week(first_group))
