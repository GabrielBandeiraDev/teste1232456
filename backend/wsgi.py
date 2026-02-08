"""
Arquivo WSGI para PythonAnywhere
"""
import sys
import os
from pathlib import Path

# Adicionar o diretório do backend ao path automaticamente
backend_dir = Path(__file__).parent.absolute()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configurar variáveis de ambiente se necessário
os.environ.setdefault('FLASK_DEBUG', 'False')

# Importar a aplicação Flask
try:
    from app import app as application
    print(f"✅ Aplicação Flask carregada com sucesso")
    print(f"📁 Diretório backend: {backend_dir}")
except Exception as e:
    print(f"❌ Erro ao carregar aplicação: {e}")
    raise

# A aplicação já está configurada no app.py
# O caminho do banco de dados será detectado automaticamente

if __name__ == "__main__":
    application.run()
