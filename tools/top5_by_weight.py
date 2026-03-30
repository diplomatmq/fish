
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import argparse
from datetime import datetime
from database import Database

def main():
    parser = argparse.ArgumentParser(description="Топ 5 пользователей по весу в чате за период")
    parser.add_argument('--chat_id', type=int, required=True, help='ID чата')
    parser.add_argument('--start', type=str, required=True, help='Время начала (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', type=str, required=True, help='Время конца (YYYY-MM-DD HH:MM:SS)')
    args = parser.parse_args()

    db = Database()
    try:
        start_dt = datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f'Ошибка в формате даты: {e}')
        return

    with db._connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                COALESCE(MAX(p.username), 'Неизвестно') AS username,
                cf.user_id,
                COALESCE(SUM(cf.weight), 0) AS total_weight
            FROM caught_fish cf
            LEFT JOIN players p ON p.user_id = cf.user_id
            WHERE cf.chat_id = ?
              AND cf.caught_at >= ?
              AND cf.caught_at <= ?
              AND COALESCE(cf.sold, 0) = 0
            GROUP BY cf.user_id
            ORDER BY total_weight DESC
            LIMIT 5
        ''', (args.chat_id, start_dt, end_dt))
        rows = cursor.fetchall()
        print(f"Топ 5 пользователей по весу в чате {args.chat_id} с {args.start} по {args.end}:")
        for i, row in enumerate(rows, 1):
            username, user_id, total_weight = row
            print(f"{i}. {username} (user_id={user_id}): {total_weight:.2f} кг")

if __name__ == '__main__':
    main()
