#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция для добавления поля stars_balance в таблицу players
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database import db

def add_stars_balance_column():
    """Добавляет поле stars_balance в таблицу players"""
    try:
        with db._connect() as conn:
            cursor = conn.cursor()
            
            # Определяем тип БД автоматически
            db_type = 'sqlite'
            try:
                cursor.execute("SELECT version()")
                version_info = cursor.fetchone()
                if version_info and 'PostgreSQL' in str(version_info[0]):
                    db_type = 'postgres'
                    print(f"Detected PostgreSQL database")
                else:
                    print(f"Detected SQLite database")
            except:
                print(f"Detected SQLite database (fallback)")
            
            # Проверяем, существует ли уже колонка stars_balance
            if db_type == 'postgres':
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='players' AND column_name='stars_balance'
                """)
                exists = cursor.fetchone()
            else:
                cursor.execute("PRAGMA table_info(players)")
                columns = cursor.fetchall()
                exists = any(col[1] == 'stars_balance' for col in columns)
            
            if not exists:
                print("Adding stars_balance column to players table...")
                if db_type == 'postgres':
                    cursor.execute("ALTER TABLE players ADD COLUMN stars_balance INTEGER DEFAULT 0")
                else:
                    cursor.execute("ALTER TABLE players ADD COLUMN stars_balance INTEGER DEFAULT 0")
                conn.commit()
                print("✅ Successfully added stars_balance column")
                
                # Копируем данные из старого поля stars (если есть)
                print("Copying data from 'stars' column to 'stars_balance'...")
                cursor.execute("UPDATE players SET stars_balance = COALESCE(stars, 0) WHERE stars IS NOT NULL")
                conn.commit()
                print("✅ Successfully copied stars data")
            else:
                print("✅ stars_balance column already exists")
                
    except Exception as e:
        print(f"❌ Error adding stars_balance column: {e}")
        raise

if __name__ == '__main__':
    db.init_db()
    add_stars_balance_column()
    print("Migration completed!")
