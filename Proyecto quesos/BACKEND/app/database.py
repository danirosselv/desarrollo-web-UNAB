import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Cargar variables de entorno desde .env
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

if not MONGO_URL:
    raise ValueError("No se encontró la variable MONGO_URL en .env")
if not DATABASE_NAME:
    raise ValueError("No se encontró la variable DATABASE_NAME en .env")

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db = Database()

async def connect_to_mongo():
    """Conecta a la base de datos MongoDB al iniciar la app."""
    print("Conectando a MongoDB...")
    db.client = AsyncIOMotorClient(MONGO_URL)
    db.db = db.client[DATABASE_NAME]
    try:
        await db.client.admin.command('ping')
        print(f"¡Conexión exitosa a MongoDB! (Base de datos: {DATABASE_NAME})")
    except Exception as e:
        print(f"Error al conectar a MongoDB: {e}")

async def close_mongo_connection():
    """Cierra la conexión a MongoDB al apagar la app."""
    print("Cerrando conexión con MongoDB...")
    db.client.close()

def get_database() -> AsyncIOMotorDatabase:
    """Devuelve la instancia de la base de datos."""
    if db.db is None:
        raise Exception("La base de datos no está inicializada. Asegúrate de llamar a connect_to_mongo().")
    return db.db

# Colecciones
# Esto es un atajo para acceder fácil a las colecciones
def get_user_collection():
    return get_database()["users"]

def get_product_collection():
    return get_database()["products"]

def get_order_collection():
    return get_database()["orders"]