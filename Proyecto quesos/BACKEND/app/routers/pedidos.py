from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict
from bson import ObjectId
from datetime import datetime

from ..models import PedidoCreate, PedidoInDB, UsuarioInDB
from ..database import get_order_collection, get_product_collection
from ..services import get_current_active_user, get_current_admin_user

router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos y Checkout"]
)

@router.post("/",
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo pedido (Checkout)"
)
async def create_order(
    pedido_in: PedidoCreate,
    current_user: UsuarioInDB = Depends(get_current_active_user)
):
    """
    Recibe el carrito finalizado y crea la orden en estado 'nuevo' (US-06).
    Esto reemplaza tu 'qs_pending_order' de localStorage.
    """
    collection = get_order_collection()
    
    # Crear pedido con userId como ObjectId
    pedido_data = pedido_in.model_dump()
    pedido_data["userId"] = ObjectId(str(current_user.id))
    pedido_data["createdAt"] = datetime.utcnow()
    pedido_data["status"] = "nuevo"
    
    # Insertar directamente sin pasar por el modelo primero
    result = await collection.insert_one(pedido_data)
    
    if result.inserted_id:
        # Recuperar el pedido insertado
        inserted = await collection.find_one({"_id": result.inserted_id})
        pedido = PedidoInDB(**inserted)
        # Devolver el pedido serializado con by_alias=False para que 'id' esté disponible
        return pedido.model_dump(by_alias=False)
        
    raise HTTPException(status_code=500, detail="Error al crear el pedido.")


@router.get("/mis-pedidos",
    response_model=List[PedidoInDB],
    summary="Obtener historial de pedidos del usuario"
)
async def get_my_orders(
    current_user: UsuarioInDB = Depends(get_current_active_user)
):
    """
    Obtiene la lista de pedidos del usuario logueado (US-10).
    """
    collection = get_order_collection()
    orders = []
    
    # Buscar usando ObjectId para consistencia
    cursor = collection.find({"userId": ObjectId(str(current_user.id))}).sort("createdAt", -1)
    
    async for order in cursor:
        # Asegurar que tenga createdAt
        if order.get("createdAt") is None:
            order["createdAt"] = datetime.utcnow()
        orders.append(PedidoInDB(**order))
        
    return orders


@router.post("/simular_pago",
    summary="Simulación del Webpay (US-07, US-08, US-09)"
)
async def simulate_payment_confirmation(
    orderId: str, 
    status_pago: str, # "ok", "rechazo", "error"
    current_user: UsuarioInDB = Depends(get_current_active_user)
):
    """
    Simula la confirmación de pago. En la vida real, esto sería un Webhook
    protegido que recibe la pasarela de pago (Webpay), no el usuario.
    """
    if not ObjectId.is_valid(orderId):
        raise HTTPException(status_code=400, detail="ID de pedido inválido")
        
    collection = get_order_collection()
    
    # Buscamos el pedido y nos aseguramos que pertenezca al usuario
    order = await collection.find_one({
        "_id": ObjectId(orderId), 
        "userId": current_user.id
    })
    
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado o no pertenece al usuario.")
        
    if order["status"] != "nuevo":
        raise HTTPException(status_code=400, detail="Este pedido ya fue procesado.")

    if status_pago == "ok":
        # (US-08)
        new_status = "en_preparacion"
        
        # Incrementar contador de ventas y decrementar stock de cada producto
        products_collection = get_product_collection()
        for item_id, item_data in order.get("items", {}).items():
            if ObjectId.is_valid(item_id):
                qty = item_data.get("qty", 0)
                await products_collection.update_one(
                    {"_id": ObjectId(item_id)},
                    {
                        "$inc": {
                            "ventas": qty,
                            "stock": -qty
                        }
                    }
                )
    else:
        # (US-09)
        new_status = "pago_fallido"

    await collection.update_one(
        {"_id": ObjectId(orderId)},
        {"$set": {"status": new_status}}
    )
    
    return {"orderId": orderId, "nuevo_status": new_status}


@router.get("/admin/todos",
    response_model=List[PedidoInDB],
    summary="Obtener todos los pedidos (Admin)"
)
async def get_all_orders(
    current_admin: UsuarioInDB = Depends(get_current_admin_user)
):
    """
    Obtiene todos los pedidos del sistema para el panel de admin.
    *Protegido: Solo Admin.*
    """
    collection = get_order_collection()
    orders = []
    
    cursor = collection.find({}).sort("createdAt", -1)
    
    async for order in cursor:
        # Asegurar que tenga createdAt
        if order.get("createdAt") is None:
            order["createdAt"] = datetime.utcnow()
        orders.append(PedidoInDB(**order))
        
    return orders


@router.put("/admin/{pedido_id}/estado",
    summary="Actualizar estado de un pedido (Admin)"
)
async def update_order_status(
    pedido_id: str,
    nuevo_estado: str,
    current_admin: UsuarioInDB = Depends(get_current_admin_user)
):
    """
    Permite al admin cambiar el estado de un pedido.
    Estados validos: nuevo, en_preparacion, enviado, entregado, cancelado
    *Protegido: Solo Admin.*
    """
    estados_validos = ["nuevo", "en_preparacion", "enviado", "entregado", "cancelado"]
    
    if nuevo_estado not in estados_validos:
        raise HTTPException(
            status_code=400, 
            detail=f"Estado invalido. Estados validos: {', '.join(estados_validos)}"
        )
    
    if not ObjectId.is_valid(pedido_id):
        raise HTTPException(status_code=400, detail="ID de pedido invalido")
    
    collection = get_order_collection()
    
    result = await collection.update_one(
        {"_id": ObjectId(pedido_id)},
        {"$set": {"status": nuevo_estado}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    
    return {"pedido_id": pedido_id, "nuevo_estado": nuevo_estado}