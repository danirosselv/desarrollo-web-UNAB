from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import List

from ..models import UsuarioCreate, UsuarioBase, Token, Direccion, UsuarioInDB
from ..database import get_user_collection
from ..services import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    get_current_active_user
)

router = APIRouter(
    tags=["Usuarios y Autenticación"]
)

@router.post("/auth/register", 
    response_model=UsuarioBase,
    status_code=status.HTTP_201_CREATED,
    summary="Registro de nuevo usuario"
)
async def register_user(user_in: UsuarioCreate):
    """
    Crea un nuevo usuario en la base de datos (US-16).
    """
    collection = get_user_collection()
    
    # Verificar si el email ya existe
    existing_user = await collection.find_one({"email": user_in.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está en uso."
        )
    
    # Hashear la contraseña
    hashed_password = get_password_hash(user_in.password)
    
    # Crear el objeto de usuario para la BD
    user_db_data = user_in.dict(exclude={"password"})
    user_db = UsuarioInDB(
        **user_db_data,
        hashed_password=hashed_password
    )
    
    # Insertar en la BD
    result = await collection.insert_one(user_db.dict(by_alias=True))
    
    if result.inserted_id:
        # Devolvemos el modelo base, sin el hash
        return UsuarioBase(**user_db_data)
        
    raise HTTPException(status_code=500, detail="Error al crear el usuario.")


@router.post("/auth/token", 
    response_model=Token,
    summary="Iniciar sesión"
)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Verifica email y contraseña, y devuelve un Token JWT (US-17).
    """
    collection = get_user_collection()
    user_data = await collection.find_one({"email": form_data.username})
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Email o contraseña incorrectos"
        )
        
    user = UsuarioInDB(**user_data)
        
    # Verificar la contraseña
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Email o contraseña incorrectos"
        )
        
    # Crear el token JWT
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", 
    response_model=UsuarioBase,
    summary="Obtener perfil del usuario actual"
)
async def read_users_me(current_user: UsuarioInDB = Depends(get_current_active_user)):
    """
    Devuelve los datos del usuario que está logueado (US-18).
    """
    # Devolvemos el modelo base, que no incluye el hash
    return UsuarioBase(**current_user.dict())


@router.post("/users/me/direcciones", 
    response_model=Direccion,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar una dirección al perfil"
)
async def add_direccion_to_user(
    direccion: Direccion,
    current_user: UsuarioInDB = Depends(get_current_active_user)
):
    """
    Añade una nueva dirección a la lista del usuario (US-18).
    """
    collection = get_user_collection()
    
    # Si es la primera, marcarla como principal
    if not current_user.direcciones:
        direccion.principal = True
        
    result = await collection.update_one(
        {"_id": current_user.id},
        {"$push": {"direcciones": direccion.dict()}}
    )
    
    if result.modified_count == 1:
        return direccion
        
    raise HTTPException(status_code=500, detail="No se pudo guardar la dirección.")