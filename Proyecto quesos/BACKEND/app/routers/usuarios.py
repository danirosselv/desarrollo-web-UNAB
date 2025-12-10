from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from bson import ObjectId

from ..models import UsuarioCreate, UsuarioBase, Token, Direccion, MetodoPago, UsuarioInDB
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
    user_db_data = user_in.model_dump(exclude={"password"})
    user_db = UsuarioInDB(
        **user_db_data,
        hashed_password=hashed_password
    )
    
    # Insertar en la BD
    result = await collection.insert_one(user_db.model_dump(by_alias=True))
    
    if result.inserted_id:
        # Devolvemos el modelo base, sin el hash
        return UsuarioBase(**user_db_data)
        
    raise HTTPException(status_code=500, detail="Error al crear el usuario.")


@router.post("/auth/token", 
    summary="Iniciar sesión"
)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Verifica email y contraseña, y devuelve un Token JWT (US-17).
    También devuelve nombre y rol del usuario.
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
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "nombre": user.nombre,
        "rol": str(user.rol)
    }


@router.get("/users/me", 
    response_model=UsuarioBase,
    summary="Obtener perfil del usuario actual"
)
async def read_users_me(current_user: UsuarioInDB = Depends(get_current_active_user)):
    """
    Devuelve los datos del usuario que está logueado (US-18).
    """
    # Devolvemos el modelo base, que no incluye el hash
    return UsuarioBase(**current_user.model_dump())


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
    try:
        collection = get_user_collection()
        
        # Intentar buscar por ObjectId primero, luego por string
        user_id_str = str(current_user.id)
        user_id_obj = ObjectId(user_id_str)
        
        # Buscar usuario (puede estar guardado como ObjectId o string)
        user_doc = await collection.find_one({"_id": user_id_obj})
        if user_doc:
            user_id = user_id_obj
        else:
            user_doc = await collection.find_one({"_id": user_id_str})
            user_id = user_id_str
        
        if not user_doc:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        current_addresses = user_doc.get("direcciones", [])
        
        # Si es la primera, marcarla como principal
        if len(current_addresses) == 0:
            direccion.principal = True
        
        # Convertir dirección a diccionario
        direccion_data = direccion.model_dump()
        
        # Usar $push para agregar la dirección
        result = await collection.update_one(
            {"_id": user_id},
            {"$push": {"direcciones": direccion_data}}
        )
        
        if result.modified_count == 1:
            return direccion
        
        # Si no se modificó, intentar con $set para crear el campo
        result = await collection.update_one(
            {"_id": user_id},
            {"$set": {"direcciones": [direccion_data]}}
        )
        
        if result.modified_count == 1 or result.matched_count == 1:
            return direccion
            
        raise HTTPException(status_code=500, detail="No se pudo guardar la dirección.")
        
    except Exception as e:
        print(f"ERROR en add_direccion: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete("/users/me/direcciones/{direccion_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar una direccion del perfil"
)
async def delete_direccion(
    direccion_id: str,
    current_user: UsuarioInDB = Depends(get_current_active_user)
):
    """
    Elimina una direccion del usuario.
    """
    collection = get_user_collection()
    
    # Buscar por ObjectId o string
    user_id_str = str(current_user.id)
    user_id_obj = ObjectId(user_id_str)
    user_doc = await collection.find_one({"_id": user_id_obj})
    user_id = user_id_obj if user_doc else user_id_str
    
    result = await collection.update_one(
        {"_id": user_id},
        {"$pull": {"direcciones": {"id": direccion_id}}}
    )
    
    if result.modified_count == 1:
        return {"message": "Direccion eliminada"}
    
    raise HTTPException(status_code=404, detail="Direccion no encontrada.")


@router.put("/users/me/direcciones/{direccion_id}/principal",
    status_code=status.HTTP_200_OK,
    summary="Establecer direccion como principal"
)
async def set_direccion_principal(
    direccion_id: str,
    current_user: UsuarioInDB = Depends(get_current_active_user)
):
    """
    Marca una direccion como principal y desmarca las demas.
    """
    collection = get_user_collection()
    
    # Buscar por ObjectId o string
    user_id_str = str(current_user.id)
    user_id_obj = ObjectId(user_id_str)
    user_doc = await collection.find_one({"_id": user_id_obj})
    if user_doc:
        user_id = user_id_obj
    else:
        user_doc = await collection.find_one({"_id": user_id_str})
        user_id = user_id_str
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    direcciones = user_doc.get("direcciones", [])
    found = False
    
    for d in direcciones:
        if d.get("id") == direccion_id:
            d["principal"] = True
            found = True
        else:
            d["principal"] = False
    
    if not found:
        raise HTTPException(status_code=404, detail="Direccion no encontrada")
    
    await collection.update_one(
        {"_id": user_id},
        {"$set": {"direcciones": direcciones}}
    )
    
    return {"message": "Direccion marcada como principal"}


@router.post("/users/me/metodos-pago", 
    response_model=MetodoPago,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar un método de pago al perfil"
)
async def add_metodo_pago_to_user(
    metodo: MetodoPago,
    current_user: UsuarioInDB = Depends(get_current_active_user)
):
    """
    Añade un nuevo método de pago a la lista del usuario.
    """
    collection = get_user_collection()
    
    # Buscar por ObjectId o string
    user_id_str = str(current_user.id)
    user_id_obj = ObjectId(user_id_str)
    user_doc = await collection.find_one({"_id": user_id_obj})
    if user_doc:
        user_id = user_id_obj
    else:
        user_doc = await collection.find_one({"_id": user_id_str})
        user_id = user_id_str
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    current_metodos = user_doc.get("metodos_pago", [])
    
    if len(current_metodos) == 0:
        metodo.principal = True
    
    metodo_data = metodo.model_dump()
    
    result = await collection.update_one(
        {"_id": user_id},
        {"$push": {"metodos_pago": metodo_data}}
    )
    
    if result.modified_count == 1:
        return metodo
    
    result = await collection.update_one(
        {"_id": user_id},
        {"$set": {"metodos_pago": [metodo_data]}}
    )
    
    if result.modified_count == 1 or result.matched_count == 1:
        return metodo
        
    raise HTTPException(status_code=500, detail="No se pudo guardar el método de pago.")


@router.delete("/users/me/metodos-pago/{metodo_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un método de pago"
)
async def delete_metodo_pago(
    metodo_id: str,
    current_user: UsuarioInDB = Depends(get_current_active_user)
):
    """
    Elimina un método de pago del usuario.
    """
    collection = get_user_collection()
    
    # Buscar por ObjectId o string
    user_id_str = str(current_user.id)
    user_id_obj = ObjectId(user_id_str)
    user_doc = await collection.find_one({"_id": user_id_obj})
    user_id = user_id_obj if user_doc else user_id_str
    
    result = await collection.update_one(
        {"_id": user_id},
        {"$pull": {"metodos_pago": {"id": metodo_id}}}
    )
    
    if result.modified_count == 1:
        return {"message": "Método de pago eliminado"}
    
    raise HTTPException(status_code=404, detail="Método de pago no encontrado.")


@router.put("/users/me/metodos-pago/{metodo_id}/principal",
    status_code=status.HTTP_200_OK,
    summary="Establecer método de pago como principal"
)
async def set_metodo_principal(
    metodo_id: str,
    current_user: UsuarioInDB = Depends(get_current_active_user)
):
    """
    Marca un método de pago como principal.
    """
    collection = get_user_collection()
    
    # Buscar por ObjectId o string
    user_id_str = str(current_user.id)
    user_id_obj = ObjectId(user_id_str)
    user_doc = await collection.find_one({"_id": user_id_obj})
    user_id = user_id_obj if user_doc else user_id_str
    
    await collection.update_one(
        {"_id": user_id},
        {"$set": {"metodos_pago.$[].principal": False}}
    )
    
    result = await collection.update_one(
        {"_id": user_id, "metodos_pago.id": metodo_id},
        {"$set": {"metodos_pago.$.principal": True}}
    )
    
    if result.modified_count == 1:
        return {"message": "Método de pago establecido como principal"}
    
    raise HTTPException(status_code=404, detail="Método de pago no encontrado.")