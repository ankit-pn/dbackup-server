import time
import os

from x import (
    is_folder_available, 
    connect_to_database, 
    get_credentials, 
    delete_request_from_database, 
    download_folder
)
from unzip_takeout import extract_all
from convert_zip import run_count_db
interval_time = os.environ.get('INTERVAL_TIME')

def background_downloader():
    print('Checking')
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, 
        folder_name TEXT,
        last_checked TEXT)
    ''')
    
    # Select all requests
    cursor.execute("SELECT * FROM requests")
    requestlist = cursor.fetchall()
    cursor.connection.commit()
    cursor.close()
    conn.close()

    for req in requestlist:
        user_id = req[1]
        folder_name = req[2]
        creds = get_credentials(user_id)
        
        if is_folder_available(folder_name, creds):
            download_folder(folder_name, creds)
            delete_request_from_database(user_id, folder_name)

    return requestlist

def scheduler():
    while True:
        background_downloader()
        extract_all()
        run_count_db()
        print('Running Scheduler...')
        time.sleep(1200)

if __name__ == "__main__":
    print('Starting Scheduler')
    scheduler()
