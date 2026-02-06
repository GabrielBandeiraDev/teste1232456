"""
Arquivo WSGI para PythonAnywhere
"""
import sys
from pathlib import Path

# Adicionar o diretório do backend ao path automaticamente
backend_dir = Path(__file__).parent.absolute()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Importar a aplicação Flask
from app import app as application

# A aplicação já está configurada no app.py
# O caminho do banco de dados será detectado automaticamente

if __name__ == "__main__":
    application.run()
