import os
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import EmailStr

from .database import get_user_collection
from .models import UsuarioInDB, TokenData

# --- Configuración de Seguridad ---

# Cargar desde .env
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

if not JWT_SECRET_KEY or not JWT_ALGORITHM:
    raise ValueError("Variables de entorno JWT no configuradas correctamente.")

# Esquema de autenticación
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Contexto para Hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Funciones de Hashing ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña plana coincide con el hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera un hash para la contraseña."""
    return pwd_context.hash(password)

# --- Funciones de Token (JWT) ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un nuevo token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

# --- Dependencia de Autenticación ---

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UsuarioInDB:
    """
    Dependencia de FastAPI para obtener el usuario actual.
    Decodifica el token JWT y busca al usuario en la BD.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub") # "sub" (subject) es nuestro email
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user_data = await get_user_collection().find_one({"email": token_data.email})
    
    if user_data is None:
        raise credentials_exception
        
    return UsuarioInDB(**user_data)

async def get_current_active_user(current_user: UsuarioInDB = Depends(get_current_user)) -> UsuarioInDB:
    """
    Dependencia que verifica si el usuario (obtenido del token) está activo.
    Por ahora, solo lo retorna. Podrías añadir lógica de 'baneo' aquí.
    """
    # if not current_user.activo:
    #     raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user

async def get_current_admin_user(current_user: UsuarioInDB = Depends(get_current_active_user)) -> UsuarioInDB:
    """Dependencia para rutas que SÓLO un admin puede usar."""
    if current_user.rol != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador."
        )
    return current_user