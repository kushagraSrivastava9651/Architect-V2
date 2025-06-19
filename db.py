import sqlite3
import os

DB_PATH = "history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_type TEXT,
            reference_file TEXT,
            client_file TEXT,
            modified_file TEXT,
            excel_file TEXT,
            reference_content BLOB,
            client_content BLOB,
            modified_content BLOB,
            excel_content BLOB,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_history(check_type, reference_file, client_file, modified_file, excel_file, 
                reference_content, client_content, modified_content, excel_content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO history (
            check_type, reference_file, client_file, modified_file, excel_file,
            reference_content, client_content, modified_content, excel_content
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (check_type, reference_file, client_file, modified_file, excel_file,
          reference_content, client_content, modified_content, excel_content))
    
    history_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return history_id

def get_all_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, check_type, reference_file, client_file, modified_file, 
               excel_file, timestamp 
        FROM history 
        ORDER BY timestamp DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_file_content(history_id, file_type):
    """
    Get file content from database by history_id and file_type
    file_type can be: 'reference', 'client', 'modified', 'excel'
    Returns tuple: (file_content, filename) or (None, None) if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if file_type == 'reference':
        cursor.execute("SELECT reference_content, reference_file FROM history WHERE id = ?", (history_id,))
    elif file_type == 'client':
        cursor.execute("SELECT client_content, client_file FROM history WHERE id = ?", (history_id,))
    elif file_type == 'modified':
        cursor.execute("SELECT modified_content, modified_file FROM history WHERE id = ?", (history_id,))
    elif file_type == 'excel':
        cursor.execute("SELECT excel_content, excel_file FROM history WHERE id = ?", (history_id,))
    else:
        conn.close()
        return None, None
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:  # Check if content exists
        return result[0], result[1]  # content, filename
    return None, None

def clear_all_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history")
    conn.commit()
    conn.close()

def delete_entry(entry_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

def get_database_size():
    """Get the size of the database file in MB"""
    if os.path.exists(DB_PATH):
        size_bytes = os.path.getsize(DB_PATH)
        size_mb = size_bytes / (1024 * 1024)
        return round(size_mb, 2)
    return 0

def cleanup_old_entries(days_old=30):
    """Remove entries older than specified days to manage database size"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM history 
        WHERE timestamp < datetime('now', '-{} days')
    """.format(days_old))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def get_entry_count():
    """Get total number of entries in the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM history")
    count = cursor.fetchone()[0]
    conn.close()
    return count