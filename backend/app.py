"""
Backend Flask para API da Altus Engenharia
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from pathlib import Path
import json

app = Flask(__name__)
CORS(app)  # Permite requisições do frontend

# Configuração do banco de dados
# PythonAnywhere: usar caminho absoluto ou relativo ao diretório atual
BASE_DIR = Path(__file__).parent.absolute()
DB_FILE = BASE_DIR / "database.db"

# Se não encontrar no diretório atual, tentar diretório pai
if not DB_FILE.exists():
    alt_path = BASE_DIR.parent / "backend" / "database.db"
    if alt_path.exists():
        DB_FILE = alt_path

def get_db_connection():
    """Cria conexão com o banco de dados SQLite"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

def row_to_dict(row):
    """Converte uma linha do SQLite para dicionário"""
    return dict(row)

@app.route('/api/health', methods=['GET'])
def health():
    """Endpoint de health check"""
    return jsonify({"status": "ok", "message": "Backend está funcionando"})

@app.route('/api/tables', methods=['GET'])
def get_tables():
    """Retorna lista de todas as tabelas disponíveis"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({"tables": tables})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/<table_name>', methods=['GET'])
def get_table_data(table_name):
    """Retorna todos os dados de uma tabela específica"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validação básica do nome da tabela (prevenção de SQL injection)
        if not table_name.replace("_", "").isalnum():
            return jsonify({"error": "Nome de tabela inválido"}), 400
        
        # Incluir rowid para facilitar operações de update/delete
        cursor.execute(f"SELECT rowid, * FROM {table_name}")
        rows = cursor.fetchall()
        conn.close()
        
        # Converter para lista de dicionários
        data = [row_to_dict(row) for row in rows]
        
        return jsonify({
            "table": table_name,
            "count": len(data),
            "data": data
        })
    except sqlite3.OperationalError as e:
        return jsonify({"error": f"Tabela '{table_name}' não encontrada", "details": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/all', methods=['GET'])
def get_all_data():
    """Retorna todos os dados de todas as tabelas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Pegar todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        result = {}
        for table_name in tables:
            cursor.execute(f"SELECT rowid, * FROM {table_name}")
            rows = cursor.fetchall()
            result[table_name] = {
                "count": len(rows),
                "data": [row_to_dict(row) for row in rows]
            }
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/<table_name>', methods=['POST'])
def add_data(table_name):
    """Adiciona novos dados a uma tabela"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
        
        # Validação do nome da tabela
        if not table_name.replace("_", "").isalnum():
            return jsonify({"error": "Nome de tabela inválido"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if not columns:
            conn.close()
            return jsonify({"error": f"Tabela '{table_name}' não encontrada"}), 404
        
        # Preparar dados para inserção
        # Se data é uma lista, inserir múltiplos registros
        if isinstance(data, list):
            records = data
        else:
            records = [data]
        
        inserted_count = 0
        for record in records:
            # Filtrar apenas colunas que existem na tabela
            filtered_record = {k: v for k, v in record.items() if k in columns}
            
            if not filtered_record:
                continue
            
            # Criar query de inserção
            columns_str = ", ".join(filtered_record.keys())
            placeholders = ", ".join(["?" for _ in filtered_record])
            values = list(filtered_record.values())
            
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            cursor.execute(query, values)
            inserted_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": f"{inserted_count} registro(s) adicionado(s) com sucesso",
            "table": table_name,
            "inserted": inserted_count
        }), 201
        
    except sqlite3.OperationalError as e:
        return jsonify({"error": f"Erro ao inserir dados: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/<table_name>/<int:record_id>', methods=['PUT'])
def update_data(table_name, record_id):
    """Atualiza um registro específico"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
        
        # Validação do nome da tabela
        if not table_name.replace("_", "").isalnum():
            return jsonify({"error": "Nome de tabela inválido"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if not columns:
            conn.close()
            return jsonify({"error": f"Tabela '{table_name}' não encontrada"}), 404
        
        # Filtrar apenas colunas que existem
        filtered_data = {k: v for k, v in data.items() if k in columns}
        
        if not filtered_data:
            conn.close()
            return jsonify({"error": "Nenhum campo válido para atualizar"}), 400
        
        # Criar query de atualização
        set_clause = ", ".join([f"{k} = ?" for k in filtered_data.keys()])
        values = list(filtered_data.values()) + [record_id]
        
        query = f"UPDATE {table_name} SET {set_clause} WHERE rowid = ?"
        cursor.execute(query, values)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Registro não encontrado"}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Registro atualizado com sucesso",
            "table": table_name,
            "id": record_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/<table_name>/<int:record_id>', methods=['DELETE'])
def delete_data(table_name, record_id):
    """Deleta um registro específico"""
    try:
        # Validação do nome da tabela
        if not table_name.replace("_", "").isalnum():
            return jsonify({"error": "Nome de tabela inválido"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f"DELETE FROM {table_name} WHERE rowid = ?"
        cursor.execute(query, (record_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Registro não encontrado"}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Registro deletado com sucesso",
            "table": table_name,
            "id": record_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/schema/<table_name>', methods=['GET'])
def get_table_schema(table_name):
    """Retorna o schema (estrutura) de uma tabela"""
    try:
        # Validação do nome da tabela
        if not table_name.replace("_", "").isalnum():
            return jsonify({"error": "Nome de tabela inválido"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        conn.close()
        
        if not columns:
            return jsonify({"error": f"Tabela '{table_name}' não encontrada"}), 404
        
        schema = [
            {
                "cid": col[0],
                "name": col[1],
                "type": col[2],
                "notnull": bool(col[3]),
                "default_value": col[4],
                "pk": bool(col[5])
            }
            for col in columns
        ]
        
        return jsonify({
            "table": table_name,
            "schema": schema
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Verificar se o banco de dados existe
    if not DB_FILE.exists():
        print(f"⚠️  Banco de dados não encontrado em {DB_FILE}")
        print("Execute primeiro: python import_excel_to_db.py")
    
    # PythonAnywhere: usar variáveis de ambiente ou porta padrão
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Iniciando servidor Flask em {host}:{port}")
    print(f"📊 Banco de dados: {DB_FILE}")
    
    app.run(debug=debug, host=host, port=port)
