import os
from datetime import timedelta, datetime, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import shutil
import uuid as uuid_mod

from database import get_db
import models, schemas

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required. Generate one with: openssl rand -hex 32")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Директорія для аватарів
AVATARS_DIR = os.path.join(os.path.dirname(__file__), "..", "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)

router = APIRouter(tags=["auth"])

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.Player).filter(models.Player.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_optional_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)), db: Session = Depends(get_db)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    user = db.query(models.Player).filter(models.Player.username == username).first()
    return user

@router.post("/register", response_model=schemas.PlayerResponse)
def register(user: schemas.PlayerCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.Player).filter(models.Player.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_email = db.query(models.Player).filter(models.Player.email == user.email).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    new_user = models.Player(username=user.username, email=user.email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Player).filter(models.Player.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.PlayerResponse)
def read_users_me(current_user: models.Player = Depends(get_current_user)):
    return current_user

@router.put("/update")
async def update_profile(
    username: str = Form(...),
    status_text: str = Form(""),
    delete_avatar: str = Form(None),
    file: UploadFile = File(None),
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Оновлення профілю: нікнейм, аватар."""
    # Перевірка на унікальність нового нікнейму
    if username != current_user.username:
        existing = db.query(models.Player).filter(models.Player.username == username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Цей нікнейм вже зайнятий")

    old_username = current_user.username
    current_user.username = username
    current_user.status_text = status_text

    # Видалення аватара
    if delete_avatar == "true":
        if current_user.avatar_url:
            old_path = os.path.join(os.path.dirname(__file__), "..", current_user.avatar_url.lstrip("/"))
            if os.path.exists(old_path):
                os.remove(old_path)
            current_user.avatar_url = None

    # Завантаження нового аватара
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1] or ".png"
        filename = f"{uuid_mod.uuid4().hex}{ext}"
        filepath = os.path.join(AVATARS_DIR, filename)
        with open(filepath, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
        current_user.avatar_url = f"/avatars/{filename}"

    db.commit()
    db.refresh(current_user)

    # Якщо нікнейм змінився — повертаємо новий токен
    result = {"message": "Профіль оновлено"}
    if username != old_username:
        access_token = create_access_token(
            data={"sub": current_user.username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        result["access_token"] = access_token

    return result

