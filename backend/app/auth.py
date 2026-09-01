from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Header
import jwt
from app.config import settings

ALGORITHM = "HS256"
EXPIRE_HOURS = 12

def create_access_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)

def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thiếu hoặc sai định dạng token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")
    return {"username": payload.get("sub"), "role": payload.get("role")}    