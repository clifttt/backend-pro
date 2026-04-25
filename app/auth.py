import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dotenv import load_dotenv

# Use bcrypt directly to avoid passlib/bcrypt version conflicts on Python 3.12
try:
    import bcrypt as _bcrypt

    def _hash_password(password: str) -> str:
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

    def _verify_password(plain: str, hashed: str) -> bool:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

except ImportError:
    # Fallback: passlib (older environments)
    from passlib.context import CryptContext
    _ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def _hash_password(password: str) -> str:
        return _ctx.hash(password)

    def _verify_password(plain: str, hashed: str) -> bool:
        return _ctx.verify(plain, hashed)


SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_ENV_VAR")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ─── Crypto ───────────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ─── Pydantic schemas for auth ────────────────────────────────────────────────
class TokenData(BaseModel):
    username: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserPublic(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Password helpers ─────────────────────────────────────────────────────────
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return _hash_password(password)


# ─── Token helpers ────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ─── DB helpers ────────────────────────────────────────────────────────────────
def get_user_by_username(db: Session, username: str):
    """Return user ORM object or None."""
    from app.models import User
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str):
    from app.models import User
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, username: str, password: str):
    """Return User if credentials valid, else None."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_user(db: Session, user_data: UserCreate):
    """Create and persist a new user. Returns User ORM object."""
    from app.models import User
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_admin=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def ensure_default_admin(db: Session) -> None:
    """Create a default admin user if no users exist yet (first-boot seed)."""
    from app.models import User
    if db.query(User).count() == 0:
        admin = User(
            username="admin",
            email="admin@investmenthub.local",
            hashed_password=get_password_hash(os.getenv("ADMIN_PASSWORD", "Admin@12345!")),
            is_active=True,
            is_admin=True,
        )
        db.add(admin)
        db.commit()


# ─── FastAPI dependency ───────────────────────────────────────────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    # Import lazily to avoid circular
):
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
        return username
    except JWTError:
        raise credentials_exception


def get_current_user_with_db(
    token: str = Depends(oauth2_scheme),
):
    """Like get_current_user but also validates user exists in DB."""
    return get_current_user(token)
