"""Punto de entrada de Fichaje. Ejecutar: python app.py."""
from FlastR import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
