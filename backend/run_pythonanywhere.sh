#!/bin/bash
# Script para rodar no PythonAnywhere (console)

echo "🚀 Iniciando Flask no PythonAnywhere..."

# Usar porta diferente da 5000 (que está em uso)
export PORT=8080
export HOST=0.0.0.0
export FLASK_DEBUG=False

# Verificar se o banco existe
if [ ! -f "database.db" ]; then
    echo "⚠️  Banco de dados não encontrado!"
    echo "Execute: python import_excel_to_db.py"
    exit 1
fi

echo "📊 Banco de dados encontrado: $(pwd)/database.db"
echo "🌐 Iniciando servidor em $HOST:$PORT"

python app.py
