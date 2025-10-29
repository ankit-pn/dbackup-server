import os.path
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import yaml
import io
from googleapiclient.http import MediaIoBaseDownload
import json
import sqlite3
from datetime import datetime, timezone
import requests
import os
import csv
import pytz
from convert_zip import convert_to_zip
from operator import itemgetter
from bot import send_message_to_telegram

def get_scope():
    with open('config.yaml','r') as file:
        config = yaml.safe_load(file)
    return config['scope']


def get_user_info(profile_service):
    response = profile_service.userinfo().get().execute()
    print(response)
    return response


def is_folder_available(folder_name, creds):
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        folder_id = get_folder_id(drive_service, folder_name)
        return folder_id != "Folder not found"
    except Exception as e:
        print(f"Error while building Google Drive service: {e}")
        # Handle or log the exception as appropriate
        return False
 

def schedule_later(user_id,folder_name):
    save_request_into_database(user_id,folder_name)
    return


def save_request_into_database(user_id,folder_name):
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute('''CREATE TABLE IF NOT EXISTS requests
                   (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                    user_id TEXT, 
                    folder_name TEXT,
                    last_checked TEXT
                   )''')
    cursor.execute("INSERT INTO requests (user_id,folder_name,last_checked) VALUES (?,?,?)",
                   (user_id, folder_name, dt_string))
    cursor.connection.commit()
    cursor.close()
    conn.close()


def delete_request_from_database(user_id,folder_name):
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM requests WHERE user_id=? AND folder_name=?", (user_id, folder_name))
    cursor.connection.commit()
    cursor.close()
    conn.close()


def get_requestlist(userid):
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS requests
                   (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                    user_id TEXT, 
                    folder_name TEXT,
                    last_checked TEXT
                   )''')
    cursor.execute(
        "SELECT id,user_id,folder_name,last_checked FROM requests where user_id=?", (userid,))
    requestlist = cursor.fetchall()
    cursor.close()
    return requestlist


def get_folder_id(drive_service, folder_name):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    response = drive_service.files().list(
        q=query,
        spaces="drive",
        fields="files(id)"
    ).execute()
    folders = response['files']
    if len(folders) > 0:
        folder_id = folders[0]['id']
        return folder_id
    else:
        return "Folder not found"


from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io
import os

def download_file_from_file_id(drive_service, file_id, path_to_save):
    try:
        file_metadata = drive_service.files().get(fileId=file_id).execute()
        file_name = file_metadata['name']
        if file_metadata['mimeType'].startswith('application/vnd.google-apps'):
            try:
                request = drive_service.files().export_media(
                    fileId=file_id, mimeType='application/pdf')
                file_name = f"{file_name}.pdf"
            except HttpError as error:
                print(f"Error exporting Google Docs file {file_name}: {error}")
                return
        else:
            request = drive_service.files().get_media(fileId=file_id)
        
        file_path = os.path.join(path_to_save, file_name)
        file_stream = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while done is False:
            try:
                status, done = downloader.next_chunk()
                print(f'Download {int(status.progress() * 100)}%.')
            except HttpError as error:
                print(f"Error downloading chunk of file {file_name}: {error}")
                file_stream.close()
                os.remove(file_path)
                return
        print(f"File downloaded: {file_path}")
    except HttpError as error:
        print(f"HTTP error occurred while downloading file {file_id}: {error}")
    except Exception as e:
        print(f"Unexpected error occurred while downloading file {file_id}: {e}")

def download_folder_by_id(folder_id, creds, path):
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        folder_content = get_folder_content(drive_service, folder_id)
        for file in folder_content:
            try:
                file_metadata = drive_service.files().get(fileId=file['id']).execute()
                file_name = file_metadata['name']
                if file_metadata['mimeType'] != 'application/vnd.google-apps.folder':
                    download_file_from_file_id(drive_service, file['id'], path)
                else:
                    new_folder_path = os.path.join(path, file_name)
                    os.makedirs(new_folder_path, exist_ok=True)
                    download_folder_by_id(file['id'], creds, new_folder_path)
            except HttpError as error:
                print(f"HTTP error occurred while processing file {file_name}: {error}")
                print("Skipping this file and continuing with others.")
            except Exception as e:
                print(f"Unexpected error occurred while processing file {file_name}: {e}")
                print("Skipping this file and continuing with others.")
    except HttpError as error:
        print(f"HTTP error occurred while processing folder {folder_id}: {error}")
    except Exception as e:
        print(f"Unexpected error occurred while processing folder {folder_id}: {e}")


def create_folder(folder_path, folder_userid, folder_name):
    current_path = os.getcwd()
    joined_path = os.path.join(current_path, folder_path)
    user_path = os.path.join(joined_path, folder_userid)
    full_path = os.path.join(user_path, folder_name)
    if not os.path.exists(full_path):
        os.makedirs(full_path)
        print("Folder Created")
    else:
        print("Folder Already Exists")


def create_folder_2(folder_path, folder_name):
    full_path = os.path.join(folder_path, folder_name)
    if not os.path.exists(full_path):
        os.makedirs(full_path)
        print("Folder Created")
    else:
        print("Folder Already Exists")



def get_path_from_email(folder_path, folder_userid, folder_name):
    current_path = os.getcwd()
    joined_path = os.path.join(current_path, folder_path)
    user_path = os.path.join(joined_path, folder_userid)
    full_path = os.path.join(user_path, folder_name)
    return full_path


def get_folder_content(drive_service, folder_id):
    query = f"'{folder_id}' in parents"
    response = drive_service.files().list(
        q=query,
        fields='files(name, id)'
    ).execute()
    print(response['files'])
    return response['files']

def connect_to_database(database):
    conn = sqlite3.connect(database)
    return conn

def _ensure_access_credentials_schema(conn):
    """Ensure access_credentials has the registered_at column for registration time."""
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS access_credentials
                   (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                    user_id TEXT, 
                    token TEXT,
                    refresh_token TEXT,
                    token_uri TEXT,
                    client_id TEXT,
                    client_secret TEXT,
                    scopes TEXT,
                    expiry TEXT
                   )""")
        cur.execute("PRAGMA table_info(access_credentials)")
        cols = [r[1] for r in cur.fetchall()]
        if 'registered_at' not in cols:
            cur.execute("ALTER TABLE access_credentials ADD COLUMN registered_at TEXT")
        conn.commit()
    except Exception:
        # Best-effort; if ALTER fails due to concurrent access, subsequent calls may succeed.
        pass

def get_credentials(user_id):
    conn = connect_to_database("credentials.db")
    _ensure_access_credentials_schema(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM access_credentials where user_id=?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.close()
        conn.close()
        return None

    token = row[2]
    refresh_token = row[3]
    token_uri = row[4]
    client_id = row[5]
    client_secret = row[6]
    scopes = json.loads(row[7])
    expiry_str = row[8]
    
    # Convert expiry_str to a datetime object
    expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S.%f")
    current_time = datetime.now(pytz.utc)
    dt = pytz.utc.localize(expiry)

    creds = Credentials(token=token, refresh_token=refresh_token, token_uri=token_uri,
                        client_id=client_id, client_secret=client_secret,
                        scopes=scopes, expiry=expiry)

    if dt < current_time:
        try:
            creds.refresh(Request())
            # Update the refreshed token back into the database
            cursor.execute('''UPDATE access_credentials
                              SET token=?, refresh_token=?, expiry=?
                              WHERE user_id=?''',
                           (creds.token, creds.refresh_token, creds.expiry, user_id))
            cursor.connection.commit()
        except RefreshError:
            print("The token has been revoked or expired. Please re-authorize the application.")
            cursor.close()
            conn.close()
            return None

    cursor.close()
    conn.close()
    return creds

def get_all_folders():
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM folders")
    rows = cursor.fetchall()
    conn.close()
    return rows




def save_credentials_without_folder(cred):
    conn = connect_to_database("credentials.db")
    _ensure_access_credentials_schema(conn)
    cursor = conn.cursor()
    profile_service = build('oauth2', 'v2', credentials=cred)
    user_id = get_user_info(profile_service)['email']
    print("Here is mt")
    print(cred.to_json())
    print(cred.token_uri)
    if check_userid_exist(user_id):
        # If user_id already exists, update the credentials for that user_id
        cursor.execute('''UPDATE access_credentials
                          SET token=?, refresh_token=?, token_uri=?, client_id=?, client_secret=?, scopes=?, expiry=?
                          WHERE user_id=?''',
                       (cred.token, cred.refresh_token, cred.token_uri, cred.client_id, cred.client_secret, json.dumps(cred.scopes), cred.expiry, user_id))
    else:
        # If user_id does not exist, insert the new credentials into the database
        registered_at = datetime.now(timezone.utc).isoformat()
        cursor.execute("INSERT INTO access_credentials (user_id,token,refresh_token,token_uri,client_id,client_secret,scopes,expiry,registered_at) VALUES (?,?,?,?,?,?,?,?,?)",
                       (user_id, cred.token, cred.refresh_token, cred.token_uri, cred.client_id, cred.client_secret, json.dumps(cred.scopes), cred.expiry, registered_at))
    
    cursor.connection.commit()
    cursor.close()

def get_user_registration_time(user_id):
    """Return registration time (UTC datetime) for a user, or None if unknown."""
    conn = connect_to_database("credentials.db")
    _ensure_access_credentials_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT registered_at FROM access_credentials WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    reg = row[0]
    if not reg:
        return None
    try:
        # Accept ISO timestamps; if naive, assume UTC
        dt = datetime.fromisoformat(reg)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def get_useremail(cred):
    profile_service = build('oauth2', 'v2', credentials=cred)
    user_email = get_user_info(profile_service)['email']
    return user_email


def check_userid_exist(user_id):
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    print(user_id)
    cursor.execute("SELECT * from access_credentials where user_id=?", (user_id,))
    row = cursor.fetchone()
    cursor.connection.commit()
    if row is None:
        return False
    else:
        return True





def get_userinfo_by_token(access_token):
    url = 'https://www.googleapis.com/oauth2/v3/userinfo'
    headers = {
    'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        user_info = response.json()
        user_email = user_info['email']
        return user_email
    else:
        print("Error occurred while fetching user information.")
        print("Response Status Code:", response.status_code)
        return "Access token is not vaild"



def save_folder_into_database(user_id,folder_name):
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute('''CREATE TABLE IF NOT EXISTS folders
                   (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                    user_id TEXT, 
                    folder_name TEXT,
                    last_backup TEXT
                   )''')
    cursor.execute("INSERT INTO folders (user_id,folder_name,last_backup) VALUES (?,?,?)",
                   (user_id, folder_name, dt_string))
    cursor.connection.commit()
    cursor.close()


def delete_folder_from_database(user_id,folder_name):
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM folders WHERE user_id=? AND folder_name=?", (user_id, folder_name))
    cursor.connection.commit()
    cursor.close()


def get_folderlist(userid):
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS folders
                   (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                    user_id TEXT, 
                    folder_name TEXT,
                    last_backup TEXT
                   )''')
    cursor.execute(
        "SELECT id,user_id,folder_name,last_backup FROM folders where user_id=?", (userid,))
    folderlist = cursor.fetchall()
    cursor.close()
    return folderlist
    






def download_folder(folder_name, creds):
    try:
        SCOPE = get_scope()
        print("Scope")
        print(SCOPE)
        print(str(creds))
        profile_service = build('oauth2', 'v2', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        print("Profile and drive service builds")
        user_info = get_user_info(profile_service)
        user_id = user_info['email']
        print("Userid")
        print(user_id)
        folder_id = get_folder_id(drive_service, folder_name)
        if folder_id == "Folder not found":
            print(f"Folder '{folder_name}' not found.")
            return
        create_folder('saved_data', user_id, folder_name)
        full_path = get_path_from_email('saved_data', user_id, folder_name)
        download_folder_by_id(folder_id, creds, path=full_path)
        print("After download")
        convert_to_zip(user_id, folder_name)
        print("After zip conversion")
        save_folder_into_database(user_id, folder_name)
        print("After saving in database")
        message = f'Successful: Folder backup successful for {user_id}.'
        send_message_to_telegram('-1002206674471', message)
    except Exception as e:
        print(f"Error in download_folder: {e}")
        message = f'Error: Folder backup failed for {user_id}. Error: {str(e)}'
        send_message_to_telegram('-1002206674471', message)


def check_drive_access(creds):
    try:
        # Build the Google Drive service
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Try to list files in the root directory
        results = drive_service.files().list(pageSize=1).execute()
        
        # If the above line doesn't throw an exception, you have access
        if results:
            return True
    except HttpError as error:
        # If an HTTP error occurs, print it and return False
        print(f"An error occurred: {error}")
        return False

def get_all_user_ids():
    user_ids = []
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM access_credentials")
    rows = cursor.fetchall()
    for row in rows:
        user_ids.append(row[0])
    cursor.close()
    conn.close()
    return user_ids

def generate_csv():
    filename = "drive_access_info.csv"
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["User ID", "Has Drive Access"])

        all_user_ids = get_all_user_ids()

        for user_id in all_user_ids:
            creds = get_credentials(user_id)
            has_access = check_drive_access(creds) if creds else False
            writer.writerow([user_id, has_access])

    return filename

# Function to parse date strings into datetime objects
def parse_date(date_string):
    return datetime.strptime(date_string, '%d/%m/%Y %H:%M:%S')

def generate_hcsv():
    filename = "history.csv"
    # Connect to credentials.db
    conn_credentials = sqlite3.connect("credentials.db")
    cursor_credentials = conn_credentials.cursor()

    # SQL JOIN Query to get unique folders with the latest backup date
    join_query = """
    SELECT hc.folder, hc.youtube_watched, hc.browser_history, MAX(f.last_backup) as last_backup
    FROM history_counts hc
    JOIN folders f ON hc.folder = f.user_id
    GROUP BY hc.folder
    """
    cursor_credentials.execute(join_query)
    records = cursor_credentials.fetchall()

    # Get field names for the CSV file
    field_names = [desc[0] for desc in cursor_credentials.description]
    cursor_credentials.close()
    conn_credentials.close()

    # Convert the last_backup date string into datetime objects and sort
    sorted_records = sorted(records, key=lambda row: parse_date(row[-1]))

    # Write sorted data to CSV file
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(field_names)  # Write the header
        for row in sorted_records:
            writer.writerow(row)  # Write the sorted records

    return filename

def generate_requests_csv():
    filename = "requests_data.csv"
    conn = sqlite3.connect("credentials.db")
    cursor = conn.cursor()

    # Execute SQL command to get all records from requests
    cursor.execute("SELECT * FROM requests")
    records = cursor.fetchall()
    field_names = [desc[0] for desc in cursor.description]

    # Close the connection
    cursor.close()
    conn.close()

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(field_names)  # Write the header
        writer.writerows(records)  # Write the records

    return filename

print('EveryThing is Ok')
