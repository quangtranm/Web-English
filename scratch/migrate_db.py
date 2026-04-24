import sqlite3
import os

db_path = 'instance/vocabulary.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(user)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'email' not in columns:
        print("Adding email column...")
        cursor.execute("ALTER TABLE user ADD COLUMN email VARCHAR(120)")
    
    if 'created_at' not in columns:
        print("Adding created_at column...")
        cursor.execute("ALTER TABLE user ADD COLUMN created_at DATETIME")
        # Update existing records with a default date
        cursor.execute("UPDATE user SET created_at = DATETIME('now') WHERE created_at IS NULL")
    
    conn.commit()
    conn.close()
    print("Migration finished successfully.")
else:
    print("Database not found")
