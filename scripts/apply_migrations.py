#!/usr/bin/env python3
"""
Apply DB migrations by instantiating the project's Database class.
Run: python scripts/apply_migrations.py
It will use the environment variable FISHBOT_DB_PATH if set, otherwise 'fishbot.initial.db'.
"""
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import top-level modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

db_path = os.environ.get('FISHBOT_DB_PATH', 'fishbot.initial.db')
os.environ['FISHBOT_DB_PATH'] = db_path

print('Using DB path:', db_path)

try:
    # Import Database after setting env so config picks up the path
    from database import Database
except Exception as e:
    print('Failed to import Database:', e)
    sys.exit(2)

try:
    Database()
    print('Database initialized / migrations applied (if any).')
except Exception as e:
    print('Error while applying migrations:', repr(e))
    sys.exit(3)
