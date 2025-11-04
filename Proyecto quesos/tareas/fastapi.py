from fastapi import FastAPI

# 1. Crear la instancia de FastAPI
app = FastAPI()

# 2. Definir un "endpoint" o ruta
#    Esto responde a peticiones GET en la raíz ("/")
@app.get("/")
def leer_raiz():
    # 3. FastAPI convierte automáticamente diccionarios de Python a JSON
    return {"mensaje": "¡Hola, esta es mi introducción a FastAPI!"}

# 4. Otra ruta de ejemplo
@app.get("/items/{item_id}")
def leer_item(item_id: int):
    # Recibe un parámetro (item_id) desde la URL
    return {"item_id": item_id, "nombre": "Item de ejemplo"}