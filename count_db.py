import os
import json
from html.parser import HTMLParser
import sqlite3

# Custom HTMLParser class for counting "Watched" keyword
class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0

    def handle_data(self, data):
        self.count += data.lower().count("watched")

# Initialize SQLite database
def db_initialize(db_name='credentials.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history_counts
                    (folder TEXT PRIMARY KEY,
                    youtube_watched INTEGER,
                    browser_history INTEGER)''')
    conn.commit()
    return conn, cursor

def db_update_or_insert(conn, cursor, folder, youtube_count=None, browser_count=None):
    cursor.execute('SELECT * FROM history_counts WHERE folder = ?', (folder,))
    row = cursor.fetchone()

    if row:
        if youtube_count is not None:
            cursor.execute('UPDATE history_counts SET youtube_watched=? WHERE folder=?', (youtube_count, folder))
        if browser_count is not None:
            cursor.execute('UPDATE history_counts SET browser_history=? WHERE folder=?', (browser_count, folder))
    else:
        youtube_value = youtube_count if youtube_count is not None else "NULL"
        browser_value = browser_count if browser_count is not None else "NULL"
        cursor.execute(f'INSERT INTO history_counts (folder, youtube_watched, browser_history) VALUES (?, {youtube_value}, {browser_value})', (folder,))

    conn.commit()


def count_watched_keyword(folder_path, conn, cursor):
    for subfolder in os.listdir(folder_path):
        # Remove the if not row: check here
        subfolder_path = os.path.join(folder_path, subfolder)
        history_path = os.path.join(subfolder_path, 'Takeout', 'Takeout', 'YouTube and YouTube Music', 'history', 'watch-history.html')
        
        if os.path.exists(history_path):
            parser = MyHTMLParser()
            with open(history_path, 'r', encoding='utf-8') as f:
                content = f.read()
                parser.feed(content)
            
            db_update_or_insert(conn, cursor, subfolder, youtube_count=parser.count)

def count_browser_history(folder_path, conn, cursor):
    for subfolder in os.listdir(folder_path):
        # Remove the if not row: check here
        subfolder_path = os.path.join(folder_path, subfolder)
        chrome_path = os.path.join(subfolder_path, 'Takeout', 'Takeout', 'Chrome')
        
        history_count = 0
        
        browser_history_path = os.path.join(chrome_path, 'BrowserHistory.json')
        if os.path.exists(browser_history_path):
            with open(browser_history_path, 'r') as f:
                data = json.load(f)
                if 'Browser History' in data:
                    history_count += len(data['Browser History'])

        history_path = os.path.join(chrome_path, 'History.json')
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                data = json.load(f)
                if 'Browser History' in data:
                    history_count += len(data['Browser History'])
        db_update_or_insert(conn, cursor, subfolder, browser_count=history_count)

def run_count_db():
    folder_path = 'saved_data'  # Replace with the actual path
    conn, cursor = db_initialize()
    count_watched_keyword(folder_path, conn, cursor)
    count_browser_history(folder_path, conn, cursor)
    print("History database has been refreshed")
    conn.close()
