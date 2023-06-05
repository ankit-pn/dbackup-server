from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import InstalledAppFlow
from starlette.requests import Request
from x import download_folder, get_scope, save_credentials_without_folder, get_useremail, check_userid_exist, get_credentials, get_userinfo_by_token, save_folder_into_database, get_folderlist, delete_folder_from_database
from urllib.parse import urljoin
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Any
from pydantic import BaseModel
import json
from convert_zip import convert_to_zip
from fastapi.responses import FileResponse
import yaml

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


client_origin_url = os.environ.get('CLIENT_ORIGIN')

app = FastAPI()
SCOPE = get_scope()

client_secret_file = 'credentials.json'

origins = [
    client_origin_url,  # Replace with the URL of your React app
    # Add any additional allowed origins
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

class AccessToken(BaseModel):
    access_token: str


class Folder(BaseModel):
    access_token: str
    folder_name: str
    scheduling_type: str


class DFolder(BaseModel):
    access_token: str
    folder_name: str





@app.post("/getfolderlist")
async def folderlist(access_token: AccessToken):
    token_str = access_token.access_token
    print(access_token.access_token)
    userid = get_userinfo_by_token(token_str)
    folder_list = get_folderlist(userid)
    print(folder_list)
    data = {
        "data": folder_list
    }
    return JSONResponse(content= data)


@app.post("/addfolder")
async def addfolder(folder: Folder):
    folder_name = folder.folder_name
    access_token = folder.access_token
    scheduling_type = folder.scheduling_type
    userid = get_userinfo_by_token(access_token)
    print(userid)
    creds = get_credentials(userid)
    
    print(creds)
    print("After Cred")
    download_folder(folder_name,creds)
    print("After download")
    convert_to_zip(userid,folder_name)
    print("After zip converstion")
    save_folder_into_database(userid,folder_name,scheduling_type)
    print("After saving in database")
    return {"Data" : "Folder Added Successfully"}


@app.post("/deletefolder")
async def deletefolder(folder: DFolder):
    folder_name = folder.folder_name
    access_token = folder.access_token
    userid = get_userinfo_by_token(access_token)
    print(userid)
    creds = get_credentials(userid)
    print(creds)
    delete_folder_from_database(userid,folder_name)
    return {"Data": "Folder Deleted Successfully"}


@app.post("/downloadfolder")
def download_file(folder: DFolder):
    access_token = folder.access_token
    folder_name = folder.folder_name
    userid = get_userinfo_by_token(access_token)
    print(userid)
    current_path = os.getcwd()
    download_file_name = f'{folder_name}.zip'
    # Replace with the actual path to your file
    rel_path = f'/saved_data/{userid}/{download_file_name}'
    file_path = current_path+rel_path
    return FileResponse(file_path, filename=download_file_name)



@app.get("/login")
async def login(request: Request):
    login_scope = ['https://www.googleapis.com/auth/userinfo.email', 'openid']
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret_file,
        login_scope,
    )
    base_url = str(request.base_url)
    print(base_url)
    redirect_uri = urljoin(base_url, "/oauth2_login_callback")
    flow.redirect_uri = redirect_uri
    authorization_url, state = flow.authorization_url(prompt="consent")
    return RedirectResponse(authorization_url)


@app.get("/oauth2_login_callback")
async def oauth2callbacklogin(request: Request):
    login_scope = ['https://www.googleapis.com/auth/userinfo.email','openid']
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret_file,
        login_scope
    )
    base_url = str(request.base_url)
    redirect_uri = urljoin(base_url, "/oauth2_login_callback")
    flow.redirect_uri = redirect_uri
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    user_id = get_useremail(credentials)
    print(user_id)
    if not check_userid_exist(user_id):
        return "response: user_id_not+found"
    else: 
        credentials = get_credentials(user_id)
        access_token = credentials.token
        redirect_url = f'{client_origin_url}/listfolder'
        response = RedirectResponse(redirect_url)
        response.set_cookie(key="access_token", value=access_token, secure=True,)
        return response

   
@app.get("/connect")
async def authorize(request: Request):
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret_file,
        SCOPE,
    )
    base_url = str(request.base_url)
    redirect_uri = urljoin(base_url, "/oauth2_connect_callback")
    flow.redirect_uri = redirect_uri
    authorization_url, state = flow.authorization_url(prompt="consent")
    return RedirectResponse(authorization_url)


# Handle the callback
@app.get("/oauth2_connect_callback")
async def oauth2callbackconnect(request: Request):
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret_file,
        SCOPE
    )
    base_url = str(request.base_url)
    redirect_uri = urljoin(base_url, "/oauth2_connect_callback")
    flow.redirect_uri = redirect_uri
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    print(credentials.to_json())
    save_credentials_without_folder(credentials)
    access_token = credentials.token
    credentials = flow.credentials

    redirect_url = f'{client_origin_url}/listfolder'
    print(redirect_url)
    response = RedirectResponse(redirect_url)
    response.set_cookie(key="access_token", value=access_token, secure=True,)
    return response
