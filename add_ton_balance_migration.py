#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция для добавления поля ton_balance в таблицу players
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database import db

def add_ton_balance_column():
    """Добавляет поле ton_balance в таблицу players"""
    try:
        with db._connect() as conn:
            cursor = conn.cursor()
            
            # Проверяем, существует ли уже колонка
            if db.DB_TYPE == 'postgres':
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='players' AND column_name='ton_balance'
                """)
                exists = cursor.fetchone()
            else:
                cursor.execute("PRAGMA table_info(players)")
                columns = cursor.fetchall()
                exists = any(col[1] == 'ton_balance' for col in columns)
            
            if not exists:
                print("Adding ton_balance column to players table...")
                if db.DB_TYPE == 'postgres':
                    cursor.execute("ALTER TABLE players ADD COLUMN ton_balance REAL DEFAULT 0")
                else:
                    cursor.execute("ALTER TABLE players ADD COLUMN ton_balance REAL DEFAULT 0")
                conn.commit()
                print("✅ Successfully added ton_balance column")
            else:
                print("✅ ton_balance column already exists")
                
    except Exception as e:
        print(f"❌ Error adding ton_balance column: {e}")
        raise

if __name__ == '__main__':
    db.init_db()
    add_ton_balance_column()
    print("Migration completed!")
