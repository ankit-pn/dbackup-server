from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import InstalledAppFlow
from starlette.requests import Request
from x import download_folder, generate_csv, generate_hcsv, get_all_folders, get_scope, save_credentials_without_folder, generate_requests_csv, get_useremail, check_userid_exist, get_credentials, get_userinfo_by_token, get_folderlist, delete_folder_from_database, is_folder_available, schedule_later, get_requestlist,delete_request_from_database
from fastapi.middleware.cors import CORSMiddleware
import os
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.responses import FileResponse

from fastapi import UploadFile, File, Form, HTTPException
import pathlib, shutil, datetime






os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


client_origin_url = os.environ.get('CLIENT_ORIGIN')
proxy_server_url = os.environ.get('PROXY_SERVER')


app = FastAPI()
SCOPE = get_scope()

client_secret_file = 'credentials.json'

origins = [
    client_origin_url
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


class DnFolder(BaseModel):
    user_id: str
    folder_name: str


@app.post("/addfolderx")
async def addfolder(folder: DnFolder):
    folder_name = folder.folder_name
    userid = folder.user_id
    scheduling_type = 1
    print(userid)
    creds = get_credentials(userid)
    if is_folder_available(folder_name,creds)==False:
        if scheduling_type=="0":
            return {"Data":"Folder Doesn't Exist"}
        else:
            schedule_later(userid,folder_name)
            return {"Data":"Folder Doesn't Exist, whenever folder get avaiable we will backup it."}
    else:
        download_folder(folder_name,creds)
        return {"Data" : "Folder Backup Successful"}


@app.get("/requests_csv/")
async def export_requests_csv():
    filename = generate_requests_csv()
    return FileResponse(filename, headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.get("/hcdata/")
async def export_csv():
    filename = generate_hcsv()
    return FileResponse(filename, headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.post("/getfolderlist")
async def folderlist(access_token: AccessToken):
    token_str = access_token.access_token
    print(access_token.access_token)
    userid = get_userinfo_by_token(token_str)
    folder_list = get_folderlist(userid)
    request_list = get_requestlist(userid)
    print(folder_list)
    data = {
        "backup_folders": folder_list,
        "request_folders": request_list
    }
    return JSONResponse(content= data)


@app.post("/addfolder")
async def addfolder(folder: Folder):
    folder_name = folder.folder_name
    access_token = folder.access_token
    scheduling_type = folder.scheduling_type
    print(scheduling_type)
    userid = get_userinfo_by_token(access_token)
    print(userid)
    creds = get_credentials(userid)
    if is_folder_available(folder_name,creds)==False:
        if scheduling_type=="0":
            return {"Data":"Folder Doesn't Exist"}
        else:
            schedule_later(userid,folder_name)
            return {"Data":"Folder Doesn't Exist, whenever folder get avaiable we will backup it."}
    else:
        download_folder(folder_name,creds)
        return {"Data" : "Folder Backup Successful"}


@app.post("/deleterequest")
async def deleterequest(folder: DFolder):
    folder_name = folder.folder_name
    access_token = folder.access_token
    userid = get_userinfo_by_token(access_token)
    print(userid)
    creds = get_credentials(userid)
    print(creds)
    delete_request_from_database(userid,folder_name)
    return {"Data": "Request Deleted Successfully"}





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


@app.get('/vdata')
def vdata():
    folder_data = get_all_folders()
    csv_content = "id,user_id,folder_name,last_backup\n"

    for row in folder_data:
        csv_content += ",".join([str(item) for item in row]) + "\n"
    return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment;filename=folders.csv"})



@app.get("/login")
async def login(request: Request):
    login_scope = ['https://www.googleapis.com/auth/userinfo.email', 'openid']
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret_file,
        login_scope,
    )
    base_url = str(request.base_url)
    print(base_url)
    redirect_uri = f'{proxy_server_url}/oauth2_login_callback'
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
    redirect_uri = f'{proxy_server_url}/oauth2_login_callback'
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
        redirect_url = f'{client_origin_url}/listfolder?token={access_token}'
        response = RedirectResponse(redirect_url)
        response.set_cookie(key="access_token", value=access_token, secure=True,samesite="None",)
        return response

   
@app.get("/connect")
async def authorize(request: Request):
    query_params = request.query_params
    param1 = query_params.get("auth-request")
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret_file,
        SCOPE,
    )
    redirect_uri = f'{proxy_server_url}/oauth2_connect_callback?auth-request={param1}'
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
    query_params = request.query_params
    param1 = query_params.get("auth-request") 
    redirect_uri = f'{proxy_server_url}/oauth2_connect_callback?auth-request={param1}'

    flow.redirect_uri = redirect_uri
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    print(credentials.to_json())
    save_credentials_without_folder(credentials)
    access_token = credentials.token
    credentials = flow.credentials
    print(param1)
    print(param1)
    print(param1)
    if param1 != 'datareq' :
        redirect_url = f'{client_origin_url}/listfolder?token={access_token}'
        response = RedirectResponse(redirect_url)
        response.set_cookie(key="access_token", value=access_token, secure=True,samesite="None",)
        return response
    else:
        redirect_url = f'{client_origin_url}/datareq?token={access_token}'
        response = RedirectResponse(redirect_url)
        response.set_cookie(key="access_token", value=access_token, secure=True,samesite="None",)
        return response

@app.get("/get_drive_access_info")
def get_drive_access_info():
    csv_file = generate_csv()
    return FileResponse(csv_file, headers={"Content-Disposition": f"attachment; filename={csv_file}"})




def sanitize_email(email: str) -> str:
    """Replace characters that cannot be used in folder names."""
    return email.replace("@", "_at_").replace("/", "_sl_")



@app.post("/upload-chatgpt-data/")
async def upload_chatgpt_data(
    email: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Save the raw ChatGPT export ZIP exactly as it is.
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files allowed")

    # base directory for all uploads (create if it doesn't exist)
    base_dir = pathlib.Path("chatgpt_uploads")
    base_dir.mkdir(parents=True, exist_ok=True)

    # user-specific folder
    user_dir = base_dir / sanitize_email(email)
    user_dir.mkdir(exist_ok=True)

    # prepend timestamp to avoid collisions
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    dest_path = user_dir / f"{timestamp}_{file.filename}"

    # save the file
    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"status": "success", "saved_to": str(dest_path)}