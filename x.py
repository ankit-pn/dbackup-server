import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import yaml
import io
from googleapiclient.http import MediaIoBaseDownload
import json
import sqlite3
import time
from datetime import datetime
import googleapiclient.discovery
from google.oauth2 import credentials
import requests
from fastapi.responses import JSONResponse
import zipfile
import os
import pytz


def get_scope():
    with open('config.yaml','r') as file:
        config = yaml.safe_load(file)
    return config['scope']


def get_user_info(profile_service):
    response = profile_service.userinfo().get().execute()
    print(response)
    return response


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
        return None
    token = row[2]
    refresh_token = row[3]
    token_uri = row[4]
    client_id = row[5]
    client_secret = row[6]
    scopes = json.loads(row[7])
    expiry_str = row[8]
    
    # Convert expiry_str to a datetime object
    # Convert expiry_str to a datetime object
    expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S.%f")

    current_time = datetime.now(pytz.utc)
    dt = pytz.utc.localize(expiry)
    if dt < current_time:
        creds.refresh(Request())
    # Create a Credentials object using the extracted fields
    creds = Credentials(token=token, refresh_token=refresh_token, token_uri=token_uri,
                        client_id=client_id, client_secret=client_secret,
                        scopes=scopes, expiry=expiry)

    

    cursor.connection.commit()
    return creds


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
    user_id_str = str(user_id)
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



def save_folder_into_database(user_id,folder_name,scheduling_type):
    conn = connect_to_database("credentials.db")
    cursor = conn.cursor()
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute('''CREATE TABLE IF NOT EXISTS folders
                   (id INTEGER PRIMARY KEY  AUTOINCREMENT,
                    user_id TEXT, 
                    folder_name TEXT,
                    scheduling_type TEXT,
                    last_backup TEXT
                   )''')
    cursor.execute("INSERT INTO folders (user_id,folder_name,scheduling_type,last_backup) VALUES (?,?,?,?)",
                   (user_id, folder_name, scheduling_type, dt_string))
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
                    scheduling_type TEXT,
                    last_backup TEXT
                   )''')
    cursor.execute(
        "SELECT * FROM folders where user_id=?", (userid,))
    folderlist = cursor.fetchall()
    return folderlist
    




def download_folder(folder_name,creds):
    SCOPE = get_scope()
    print("Scope")
    print(SCOPE)
    print(str(creds))
    profile_service = build('oauth2', 'v2', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    print("Profile and drive sevice buiulds")
    user_info = get_user_info(profile_service)
    user_id = user_info['email']
    print("Userid")
    print(user_id)
    folder_id = get_folder_id(drive_service,folder_name)
    folder_content = get_folder_content(drive_service, folder_id)
    create_folder('saved_data', user_id, folder_name)
    full_path = get_path_from_email('saved_data', user_id, folder_name)
    for file in folder_content:
        download_file_from_file_id(drive_service, file['id'], full_path)




# print(get_scope())
# main("Takeout")

__all__ = ['download_folder', 'get_scope', 'save_credentials_without_folder', 'get_useremail', 'check_userid_exist',
           'get_userinfo_by_token', 'save_folder_into_database', 'get_folderlist', 'delete_folder_from_database','zip_folder']

print('EveryThing is Ok')
