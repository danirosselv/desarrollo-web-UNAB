from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import connect_to_mongo, close_mongo_connection
from .routers import productos, usuarios, pedidos

# Crear la aplicación FastAPI
app = FastAPI(
    title="Queso & Sabor API",
    description="Backend para el MVP de la tienda de quesos.",
    version="1.0.0"
)

# --- Configuración de CORS ---
# ¡MUY IMPORTANTE! Esto permite que tu frontend (HTML)
# se comunique con este backend.
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:5500", # Puerto común de Live Server en VSCode
    "null", # Para permitir archivos locales (file://)
    # Deberías añadir aquí el dominio de tu frontend si lo despliegas
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos los métodos (GET, POST, PUT, etc.)
    allow_headers=["*"], # Permite todos los headers
)

# --- Eventos de Ciclo de Vida (Startup/Shutdown) ---

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

# --- Inclusión de Routers ---

app.include_router(usuarios.router)
app.include_router(productos.router)
app.include_router(pedidos.router)

# --- Endpoint Raíz ---

@app.get("/", tags=["Root"])
async def read_root():
    return {"proyecto": "API de Queso & Sabor v1.0"}