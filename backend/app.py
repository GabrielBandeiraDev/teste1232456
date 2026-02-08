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
# CORS configurado para aceitar requisições de qualquer origem (produção)
# Para desenvolvimento, pode restringir aos domínios específicos
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],  # Aceita de qualquer origem
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuração do banco de dados
# PythonAnywhere: usar caminho absoluto ou relativo ao diretório atual
BASE_DIR = Path(__file__).parent.absolute()
DB_FILE = BASE_DIR / "database.db"

# Se não encontrar no diretório atual, tentar diferentes caminhos (PythonAnywhere)
if not DB_FILE.exists():
    # Tentar diretório pai/backend
    alt_path = BASE_DIR.parent / "backend" / "database.db"
    if alt_path.exists():
        DB_FILE = alt_path
    else:
        # Tentar diretório home do PythonAnywhere
        home_path = Path.home() / "mysite" / "backend" / "database.db"
        if home_path.exists():
            DB_FILE = home_path
        else:
            # Tentar caminho absoluto comum no PythonAnywhere
            pythonanywhere_path = Path("/home") / os.environ.get("USER", "") / "mysite" / "backend" / "database.db"
            if pythonanywhere_path.exists():
                DB_FILE = pythonanywhere_path

def get_db_connection():
    """Cria conexão com o banco de dados SQLite"""
    try:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        print(f"Caminho tentado: {DB_FILE}")
        raise

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
    """Retorna todos os dados de uma tabela específica, com filtros opcionais por mês e ano"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validação básica do nome da tabela (prevenção de SQL injection)
        # Permite letras, números e underscores
        if not table_name.replace("_", "").replace("-", "").isalnum():
            return jsonify({"error": "Nome de tabela inválido"}), 400
        
        # Verificar estrutura da tabela para saber quais colunas existem
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        # Parâmetros de filtro opcionais
        mes = request.args.get('mes', '').strip()
        ano = request.args.get('ano', '').strip()
        
        # Construir query com filtros opcionais
        query = f"SELECT rowid, * FROM {table_name}"
        conditions = []
        params = []
        
        # Verificar se a tabela tem colunas de mês e ano
        has_mes_col = any('mês' in col.lower() or 'mes' in col.lower() for col in column_names)
        has_ano_col = any('ano' in col.lower() for col in column_names)
        
        # Tentar encontrar colunas de mês e ano (case-insensitive)
        mes_col = None
        ano_col = None
        
        for col in column_names:
            col_lower = col.lower()
            if not mes_col and ('mês' in col_lower or 'mes' in col_lower):
                mes_col = col
            if not ano_col and 'ano' in col_lower:
                ano_col = col
        
        # Aplicar filtros se as colunas existirem e os parâmetros foram fornecidos
        if mes_col and mes:
            conditions.append(f"{mes_col} = ?")
            params.append(mes)
        
        if ano_col and ano:
            try:
                ano_int = int(ano)
                conditions.append(f"{ano_col} = ?")
                params.append(ano_int)
            except ValueError:
                pass  # Ignorar se ano não for numérico
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Executar query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Converter para lista de dicionários
        data = [row_to_dict(row) for row in rows]
        
        return jsonify({
            "table": table_name,
            "count": len(data),
            "data": data,
            "filters": {
                "mes": mes if mes else None,
                "ano": ano if ano else None
            }
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
        
        # Validação do nome da tabela (permite letras, números, underscores e hífens)
        if not table_name.replace("_", "").replace("-", "").isalnum():
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
        
        # Validação do nome da tabela (permite letras, números, underscores e hífens)
        if not table_name.replace("_", "").replace("-", "").isalnum():
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
        # Validação do nome da tabela (permite letras, números, underscores e hífens)
        if not table_name.replace("_", "").replace("-", "").isalnum():
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
        # Validação do nome da tabela (permite letras, números, underscores e hífens)
        if not table_name.replace("_", "").replace("-", "").isalnum():
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

@app.route('/api/data/<table_name>/filters', methods=['GET'])
def get_table_filters(table_name):
    """Retorna os valores únicos de mês e ano disponíveis em uma tabela"""
    try:
        # Validação do nome da tabela (permite letras, números, underscores e hífens)
        if not table_name.replace("_", "").replace("-", "").isalnum():
            return jsonify({"error": "Nome de tabela inválido"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        # Encontrar colunas de mês e ano
        mes_col = None
        ano_col = None
        
        for col in column_names:
            col_lower = col.lower()
            if not mes_col and ('mês' in col_lower or 'mes' in col_lower):
                mes_col = col
            if not ano_col and 'ano' in col_lower:
                ano_col = col
        
        meses = []
        anos = []
        
        if mes_col:
            cursor.execute(f"SELECT DISTINCT {mes_col} FROM {table_name} WHERE {mes_col} IS NOT NULL AND {mes_col} != ''")
            meses = [row[0] for row in cursor.fetchall() if row[0]]
        
        if ano_col:
            cursor.execute(f"SELECT DISTINCT {ano_col} FROM {table_name} WHERE {ano_col} IS NOT NULL AND {ano_col} != ''")
            anos = [int(row[0]) for row in cursor.fetchall() if row[0] and str(row[0]).isdigit()]
            anos = sorted(set(anos), reverse=True)  # Ordenar do mais recente para o mais antigo
        
        conn.close()
        
        return jsonify({
            "table": table_name,
            "meses": meses,
            "anos": anos,
            "columns": {
                "mes": mes_col,
                "ano": ano_col
            }
        })
        
    except sqlite3.OperationalError as e:
        return jsonify({"error": f"Tabela '{table_name}' não encontrada", "details": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Verificar se o banco de dados existe
    if not DB_FILE.exists():
        print(f"⚠️  Banco de dados não encontrado em {DB_FILE}")
        print("Execute primeiro: python import_excel_to_db.py")
        print(f"📁 Diretório atual: {BASE_DIR}")
        print(f"📁 Caminho absoluto: {DB_FILE.absolute()}")
    else:
        print(f"✅ Banco de dados encontrado: {DB_FILE}")
    
    # PythonAnywhere: usar variáveis de ambiente ou porta padrão
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Iniciando servidor Flask em {host}:{port}")
    print(f"📊 Banco de dados: {DB_FILE}")
    print(f"🌐 Ambiente: {'Desenvolvimento' if debug else 'Produção'}")
    
    app.run(debug=debug, host=host, port=port)
