from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from pydantic_core import core_schema
from enum import Enum 

# --- Utilidad para manejar ObjectId de Mongo ---

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """
        Define cómo Pydantic v2 debe validar y serializar este tipo.
        """
        def validate_object_id(v):
            if isinstance(v, ObjectId):
                return v
            if not ObjectId.is_valid(v):
                raise ValueError('Invalid ObjectId')
            return ObjectId(v)
        
        validator = core_schema.no_info_plain_validator_function(validate_object_id)

        return core_schema.json_or_python_schema(
            json_schema=validator,
            python_schema=validator,
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """
        Define cómo debe ser el schema en Swagger/OpenAPI.
        (ESTA FUNCIÓN FUE CORREGIDA)
        """
        # Simplemente le decimos que es un string con formato 'objectid'.
        return {
            'type': 'string',
            'format': 'objectid',
            'example': '5eb7cf3a00f20beadae12345'
        }


# --- Modelos de Usuario (US-16, US-17, US-18) ---

class Direccion(BaseModel):
    id: str = Field(default_factory=lambda: str(datetime.now().timestamp()))
    texto: str
    comuna: str
    principal: bool = False

class UsuarioBase(BaseModel):
    email: EmailStr
    nombre: str
    direcciones: List[Direccion] = []
    rol: str = "CLIENTE"

class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre: str
    password: str = Field(..., min_length=8)

class UsuarioInDB(UsuarioBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        arbitrary_types_allowed=True
    )
        
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


# --- Modelos de Producto (US-01, 02, 13, 14, 15) ---

class TipoLecheEnum(str, Enum):
    VACA = "vaca"
    CABRA = "cabra"
    OVEJA = "oveja"

class ProductoBase(BaseModel):
    nombre: str
    precio: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    leche: TipoLecheEnum
    descripcion: Optional[str] = ""
    imagen: Optional[str] = ""
    activo: bool = True
    
class ProductoCreate(ProductoBase):
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

class ProductoInDB(ProductoCreate):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    
    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        arbitrary_types_allowed=True,
        use_enum_values=True 
    )

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    precio: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    leche: Optional[TipoLecheEnum] = None
    descripcion: Optional[str] = None
    imagen: Optional[str] = None
    activo: Optional[bool] = None
    updatedAt: datetime = Field(default_factory=datetime.utcnow)


# --- Modelos de Pedido (US-04, 06, 10, 11, 12) ---

class ItemCarrito(BaseModel):
    id: str
    nombre: str
    precio: float
    qty: int

class Buyer(BaseModel):
    nombre: str
    email: EmailStr
    dire: str

class ShippingDetail(BaseModel):
    comuna: Optional[str] = None
    sucursal: Optional[str] = None

class PedidoCreate(BaseModel):
    buyer: Buyer
    items: dict[str, ItemCarrito]
    subtotal: float
    shipping: float
    total: float
    shippingMethod: str
    shippingDetail: ShippingDetail
    
class PedidoInDB(PedidoCreate):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    userId: Optional[PyObjectId] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    status: str = "nuevo"
    
    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        arbitrary_types_allowed=True
    )