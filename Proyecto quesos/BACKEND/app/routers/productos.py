from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import List
from bson import ObjectId

from ..models import ProductoCreate, ProductoInDB, ProductoUpdate
from ..database import get_product_collection
from ..services import get_current_admin_user

router = APIRouter(
    prefix="/productos",
    tags=["Productos"]
)

@router.post("/", 
    response_model=ProductoInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo producto (Admin)"
)
async def create_product(
    producto: ProductoCreate,
    # current_admin: UsuarioInDB = Depends(get_current_admin_user) # Descomentar para proteger
):
    """
    Crea un nuevo producto en la base de datos (US-13).
    *Protegido: Solo Admin.*
    """
    collection = get_product_collection()
    
    # Insertar en la base de datos
    result = await collection.insert_one(producto.dict())
    
    # Recuperar el producto insertado para devolverlo
    new_product = await collection.find_one({"_id": result.inserted_id})
    if new_product:
        return ProductoInDB(**new_product)
    
    raise HTTPException(status_code=400, detail="No se pudo crear el producto.")

@router.get("/", 
    response_model=List[ProductoInDB],
    summary="Listar todos los productos"
)
async def get_all_products():
    """
    Obtiene la lista de todos los productos activos (US-01, US-02, US-03).
    *Abierto al público.*
    """
    collection = get_product_collection()
    products = []
    cursor = collection.find({"activo": True})
    
    async for prod in cursor:
        products.append(ProductoInDB(**prod))
        
    return products

@router.get("/{id}", 
    response_model=ProductoInDB,
    summary="Obtener un producto por ID"
)
async def get_product_by_id(id: str):
    """
    Obtiene los detalles de un solo producto por su ID (US-03).
    *Abierto al público.*
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="ID de producto inválido")
        
    collection = get_product_collection()
    product = await collection.find_one({"_id": ObjectId(id)})
    
    if product:
        return ProductoInDB(**product)
        
    raise HTTPException(status_code=404, detail=f"Producto con id {id} no encontrado")

@router.put("/{id}", 
    response_model=ProductoInDB,
    summary="Actualizar un producto (Admin)"
)
async def update_product(
    id: str,
    update_data: ProductoUpdate,
    # current_admin: UsuarioInDB = Depends(get_current_admin_user) # Descomentar para proteger
):
    """
    Actualiza el precio, stock, imagen, etc., de un producto (US-14, US-15).
    *Protegido: Solo Admin.*
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="ID de producto inválido")

    collection = get_product_collection()
    
    # Construir el objeto de actualización, quitando valores nulos
    update_dict = update_data.dict(exclude_unset=True)
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")

    result = await collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Producto con id {id} no encontrado")
        
    updated_product = await collection.find_one({"_id": ObjectId(id)})
    return ProductoInDB(**updated_product)