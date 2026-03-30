
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import argparse
from datetime import datetime
from database import Database



    parser = argparse.ArgumentParser(description="Суммарный вес по списку пользователей за период")
    parser.add_argument('--user_ids', type=str, required=True, help='Список user_id через запятую, без пробелов')
    parser.add_argument('--start', type=str, required=True, help='Время начала (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', type=str, required=True, help='Время конца (YYYY-MM-DD HH:MM:SS)')
    args = parser.parse_args()

    try:
        user_ids = [int(uid) for uid in args.user_ids.split(',') if uid.strip()]
    except Exception as e:
        print(f'Ошибка в user_ids: {e}')
        return

    db = Database()
    try:
        start_dt = datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f'Ошибка в формате даты: {e}')
        return

    with db._connect() as conn:
        cursor = conn.cursor()
        results = []
        for uid in user_ids:
            cursor.execute('''
                SELECT COALESCE(MAX(p.username), 'Неизвестно') AS username,
                       COALESCE(SUM(cf.weight), 0) AS total_weight
                FROM caught_fish cf
                LEFT JOIN players p ON p.user_id = cf.user_id
                WHERE cf.user_id = ?
                  AND cf.caught_at >= ?
                  AND cf.caught_at <= ?
                  AND COALESCE(cf.sold, 0) = 0
            ''', (uid, start_dt, end_dt))
            row = cursor.fetchone()
            username, total_weight = row
            results.append((uid, username, total_weight))

        print(f"Суммарный вес по пользователям за период {args.start} — {args.end}:")
        if not results:
            print("Нет данных за выбранный период.")
        else:
            for i, (uid, username, total_weight) in enumerate(results, 1):
                print(f"{i}. {username} (user_id={uid}): {total_weight:.2f} кг")
if __name__ == '__main__':
    main()
