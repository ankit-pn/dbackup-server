import time
import os
from datetime import datetime, timezone
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build

from x import (
    is_folder_available, 
    connect_to_database, 
    get_credentials, 
    delete_request_from_database, 
    download_folder,
    get_user_registration_time
)
from unzip_takeout import extract_all
from count_db import run_count_db

# Interval time (seconds); allow override via env
try:
    interval_time = int(os.getenv('INTERVAL_TIME', '600'))
except Exception:
    interval_time = 600

# Optional cutoff date for user registrations. If set, only users registered
# at or after this datetime are processed. ISO 8601 expected (e.g., 2024-07-01 or 2024-07-01T00:00:00Z)
def _parse_cutoff(value: str):
    if not value:
        return None
    try:
        v = value.strip()
        # Normalize trailing Z to +00:00 for fromisoformat
        if v.endswith('Z'):
            v = v[:-1] + '+00:00'
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

_CUTOFF_STR = os.getenv('REGISTRATION_CUTOFF_DATE', '').strip()
REGISTRATION_CUTOFF = _parse_cutoff(_CUTOFF_STR)

def download_folder_safely(folder_name, creds):
    try:
        download_folder(folder_name, creds)
        return True
    except Exception as e:
        print(f"Error downloading folder {folder_name}: {e}")
        print("Skipping this folder and continuing with others.")
        return False

def background_downloader():
    try:
        print('Checking for download requests')
        conn = connect_to_database("credentials.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, 
            folder_name TEXT,
            last_checked TEXT)
        ''')
        
        cursor.execute("SELECT * FROM requests")
        requestlist = cursor.fetchall()
        cursor.connection.commit()
        cursor.close()
        conn.close()

        successful_downloads = 0

        for req in requestlist:
            try:
                user_id = req[1]
                folder_name = req[2]
                creds = get_credentials(user_id)
                # If a cutoff is set, skip users registered before it or without a known registration time
                if REGISTRATION_CUTOFF is not None:
                    reg_time = get_user_registration_time(user_id)
                    if (reg_time is None) or (reg_time < REGISTRATION_CUTOFF):
                        # Skip this request due to cutoff
                        continue
                
                if creds and is_folder_available(folder_name, creds):
                    if download_folder_safely(folder_name, creds):
                        delete_request_from_database(user_id, folder_name)
                        successful_downloads += 1
            except Exception as e:
                print(f"Error processing request for user {user_id}: {e}")
                print("Continuing with next request.")
                
        return successful_downloads
    except Exception as e:
        print(f"Error in background_downloader: {e}")
        return 0

def log_scheduler_run(successful_downloads):
    log_file = "/dbackup-server/logs/scheduler_log.txt"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{current_time} - Successfully downloaded: {successful_downloads}\n"
    
    with open(log_file, "a") as f:
        f.write(log_entry)

def scheduler():
    while True:
        try:
            successful_downloads = background_downloader()
            extract_all()
            run_count_db()
            log_scheduler_run(successful_downloads)
        except Exception as e:
            print(f"Error in scheduler loop: {e}")
        print('Scheduler cycle completed. Waiting for next cycle...')
        time.sleep(interval_time)

if __name__ == "__main__":
    print('Starting Scheduler')
    scheduler()
