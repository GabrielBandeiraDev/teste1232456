#!/bin/bash
# Script para iniciar o backend Flask

echo "🚀 Iniciando backend Flask..."

# Verificar se o venv existe
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar venv
source venv/bin/activate

# Verificar se as dependências estão instaladas
if ! python -c "import flask" 2>/dev/null; then
    echo "📥 Instalando dependências..."
    pip install -r requirements.txt
fi

# Verificar se o banco de dados existe
if [ ! -f "database.db" ]; then
    echo "📊 Importando dados do Excel para SQLite..."
    python import_excel_to_db.py
fi

# Iniciar servidor
echo "✅ Iniciando servidor Flask na porta 5000..."
python app.py
