import pyodbc
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import user_store
from app.auth import create_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    role: str

class RegisterRequest(BaseModel):
    username: str
    password: str

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    role = user_store.verify_user(request.username, request.password)
    if role is None:
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không hợp lệ")
    return LoginResponse(access_token=create_access_token(request.username, role), role=role)


@router.post("/register", status_code=204)
def register(request: RegisterRequest):
    # Role luon la "user" - khong nhan tu client de tranh tu leo thang quyen.
    username = request.username.strip()
    if not username or not request.password:
        raise HTTPException(status_code=400, detail="Tên đăng nhập và mật khẩu không được để trống")
    try:
        user_store.create_user(username, request.password, role="user")
    except pyodbc.IntegrityError:
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại")