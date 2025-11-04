from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict
from bson import ObjectId

from ..models import PedidoCreate, PedidoInDB, UsuarioInDB
from ..database import get_order_collection
from ..services import get_current_active_user

router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos y Checkout"]
)

@router.post("/",
    response_model=PedidoInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo pedido (Checkout)"
)
async def create_order(
    pedido_in: PedidoCreate,
    current_user: UsuarioInDB = Depends(get_current_active_user) # Opcional si permites invitados
):
    """
    Recibe el carrito finalizado y crea la orden en estado 'nuevo' (US-06).
    Esto reemplaza tu 'qs_pending_order' de localStorage.
    """
    collection = get_order_collection()
    
    pedido_db = PedidoInDB(
        **pedido_in.dict(),
        userId=current_user.id # Asocia el pedido al usuario logueado
    )
    
    result = await collection.insert_one(pedido_db.dict(by_alias=True))
    
    if result.inserted_id:
        # Devolvemos el pedido completo con su nuevo ID
        return pedido_db
        
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
    
    cursor = collection.find({"userId": current_user.id}).sort("createdAt", -1)
    
    async for order in cursor:
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
        # Aquí también deberías descontar el stock de los productos (lógica futura)
    else:
        # (US-09)
        new_status = "pago_fallido"

    await collection.update_one(
        {"_id": ObjectId(orderId)},
        {"$set": {"status": new_status}}
    )
    
    return {"orderId": orderId, "nuevo_status": new_status}