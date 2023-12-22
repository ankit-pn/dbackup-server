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
from datetime import datetime
import requests
import os
import csv
import pytz
from convert_zip import convert_to_zip


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


def download_file_from_file_id(drive_service, file_id, path_to_save):
    file_metadata = drive_service.files().get(fileId=file_id).execute()
    file_name = file_metadata['name']
    if file_metadata['mimeType'].startswith('application/vnd.google-apps'):
        request = drive_service.files().export_media(
            fileId=file_id, mimeType='application/pdf')
        file_name = F"{file_name}.pdf"
    else:
        request = drive_service.files().get_media(fileId=file_id)
    file_path = os.path.join(path_to_save, file_name)
    file_stream = io.FileIO(file_path, 'wb')
    downloader = MediaIoBaseDownload(file_stream, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print(F'Download {int(status.progress()*100)}.')
    print(f"File downloaded: {file_path}")


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

def get_credentials(user_id):
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS access_credentials
                   (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                    user_id TEXT, 
                    token TEXT,
                    refresh_token TEXT,
                    token_uri TEXT,
                    client_id TEXT,
                    client_secret TEXT,
                    scopes TEXT,
                    expiry TEXT
                   )''')
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
    cursor = conn.cursor()
    profile_service = build('oauth2', 'v2', credentials=cred)
    user_id = get_user_info(profile_service)['email']
    cursor.execute('''CREATE TABLE IF NOT EXISTS access_credentials
                   (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                    user_id TEXT, 
                    token TEXT,
                    refresh_token TEXT,
                    token_uri TEXT,
                    client_id TEXT,
                    client_secret TEXT,
                    scopes TEXT,
                    expiry TEXT
                   )''')
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
        cursor.execute("INSERT INTO access_credentials (user_id,token,refresh_token,token_uri,client_id,client_secret,scopes,expiry) VALUES (?,?,?,?,?,?,?,?)",
                       (user_id, cred.token, cred.refresh_token, cred.token_uri, cred.client_id, cred.client_secret, json.dumps(cred.scopes), cred.expiry))
    
    cursor.connection.commit()
    cursor.close()


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
    



def download_folder_by_id(folder_id,creds,path):
    drive_service = build('drive', 'v3', credentials=creds)
    folder_content = get_folder_content(drive_service, folder_id)
    for file in folder_content:
        file_metadata = drive_service.files().get(fileId=file['id']).execute()
        file_name = file_metadata['name']
        if file_metadata['mimeType']!='application/vnd.google-apps.folder':
            download_file_from_file_id(drive_service, file['id'], path)
        else:
            create_folder_2(path,file_name)
            next_path = os.path.join(path, file_name)
            download_folder_by_id(file['id'],creds,next_path)
    



def download_folder(folder_name,creds):
    SCOPE = get_scope()
    print("Scope")
    print(SCOPE)
    print(str(creds))
    profile_service = build('oauth2', 'v2', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    print("Profile and drive sevice builds")
    user_info = get_user_info(profile_service)
    user_id = user_info['email']
    print("Userid")
    print(user_id)
    folder_id = get_folder_id(drive_service,folder_name)
    create_folder('saved_data', user_id, folder_name)
    full_path = get_path_from_email('saved_data', user_id, folder_name)
    download_folder_by_id(folder_id,creds,path=full_path)
    print("After download")
    convert_to_zip(user_id,folder_name)
    print("After zip converstion")
    save_folder_into_database(user_id,folder_name)
    print("After saving in database")


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

def generate_hcsv():
    filename = "history_counts.csv"
    conn = sqlite3.connect("counts.db")
    cursor = conn.cursor()

    # Execute SQL command to get all records from history_counts
    cursor.execute("SELECT * FROM history_counts")
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
