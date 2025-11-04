from flask import Flask

# 1. Crear una instancia de la aplicación Flask
app = Flask(__name__)

# 2. Definir una ruta (la página principal "/")
@app.route("/")
def hola_mundo():
    # 3. Lo que devuelve la función es lo que se verá en el navegador
    return "¡Hola, este es mi primer backend básico!"

# Esto es necesario para ejecutar el servidor al correr el script
if __name__ == "__main__":
    app.run(debug=True)