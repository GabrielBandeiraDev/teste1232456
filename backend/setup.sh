#!/bin/bash
# Script de setup do backend

echo "🚀 Configurando backend Flask..."

# Criar venv se não existir
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar venv e instalar dependências
echo "📥 Instalando dependências..."
source venv/bin/activate
pip install -r requirements.txt

# Importar dados do Excel
echo "📊 Importando dados do Excel para SQLite..."
python import_excel_to_db.py

echo "✅ Setup concluído!"
echo ""
echo "Para iniciar o servidor, execute:"
echo "  source venv/bin/activate"
echo "  python app.py"
