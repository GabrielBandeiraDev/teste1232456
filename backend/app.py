"""
Backend Flask para API da Altus Engenharia
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from pathlib import Path
import json
import re
from datetime import datetime
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️  pdfplumber não instalado. Instale com: pip install pdfplumber")

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
    """Converte uma linha do SQLite para dicionário, tratando tipos especiais"""
    result = {}
    for key in row.keys():
        value = row[key]
        # Converter None para null (JSON)
        if value is None:
            result[key] = None
        # Manter strings, números e booleanos como estão
        elif isinstance(value, (str, int, float, bool)):
            result[key] = value
        # Converter bytes para string (se necessário)
        elif isinstance(value, bytes):
            result[key] = value.decode('utf-8', errors='ignore')
        # Converter outros tipos para string
        else:
            result[key] = str(value)
    return result

@app.route('/', methods=['GET'])
def index():
    """Página de teste para upload de PDF"""
    return send_from_directory(BASE_DIR, 'index.html')

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
            # Converter nome do mês para número (1-12) para comparação com datas ISO
            meses_nomes = {
                'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3,
                'abril': 4, 'maio': 5, 'junho': 6,
                'julho': 7, 'agosto': 8, 'setembro': 9,
                'outubro': 10, 'novembro': 11, 'dezembro': 12
            }
            
            mes_lower = mes.lower().strip()
            mes_num = meses_nomes.get(mes_lower)
            
            # Construir condição que funciona tanto para datas ISO quanto para nomes de meses
            # SQLite: strftime('%m', datetime_field) retorna '01'-'12' como string
            if mes_num:
                # Tentar múltiplas formas: data ISO (extrair mês), nome do mês, número
                conditions.append(
                    f"(CAST(strftime('%m', {mes_col}) AS INTEGER) = ? OR "
                    f"LOWER(TRIM({mes_col})) = LOWER(?) OR "
                    f"CAST({mes_col} AS INTEGER) = ?)"
                )
                params.extend([mes_num, mes, mes_num])
            else:
                # Comparação direta (pode ser número ou formato diferente)
                conditions.append(f"(LOWER(TRIM({mes_col})) = LOWER(?) OR {mes_col} = ?)")
                params.extend([mes, mes])
        
        if ano_col and ano:
            try:
                ano_int = int(ano)
                # Se temos campo de mês que pode ser data, também filtrar por ano na data
                if mes_col:
                    conditions.append(
                        f"((CAST(strftime('%Y', {mes_col}) AS INTEGER) = ?) OR ({ano_col} = ?))"
                    )
                    params.extend([ano_int, ano_int])
                else:
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

# Tabelas permitidas para zerar (segurança: evitar apagar outras tabelas)
CLEAR_ALLOWED_TABLES = {'absenteísmo', 'base_kpi'}

@app.route('/api/data/<table_name>/clear', methods=['POST'])
def clear_table(table_name):
    """Zera todos os registros de uma tabela (apenas tabelas permitidas)."""
    try:
        if table_name not in CLEAR_ALLOWED_TABLES:
            return jsonify({"error": f"Tabela não permitida para zerar. Permitidas: {list(CLEAR_ALLOWED_TABLES)}"}), 400
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.execute(f"DELETE FROM {table_name}")
        conn.commit()
        conn.close()
        return jsonify({
            "message": f"Tabela '{table_name}' zerada com sucesso",
            "registros_removidos": count
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

@app.route('/api/upload/folha-ponto', methods=['POST'])
def upload_folha_ponto():
    """Processa PDF de folha de ponto e extrai dados de absenteísmo, horas extras e custos"""
    if not PDF_AVAILABLE:
        return jsonify({"error": "Biblioteca pdfplumber não está instalada"}), 500
    
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nome de arquivo vazio"}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Arquivo deve ser PDF"}), 400
    
    try:
        # Salvar arquivo temporariamente
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # Extrair dados do PDF
        dados_extraidos = extrair_dados_folha_ponto(tmp_path)
        
        # Limpar arquivo temporário
        os.unlink(tmp_path)
        
        # Validar dados extraídos
        if not dados_extraidos:
            return jsonify({
                "error": "Nenhum dado foi extraído do PDF",
                "message": "Verifique se o formato do PDF está correto ou se contém os dados esperados"
            }), 400
        
        # Inserir dados no banco
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Criar tabela absenteísmo se não existir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS absenteísmo (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                CPF TEXT,
                Nome TEXT,
                Mês TEXT,
                Ano INTEGER,
                Horas_Extras REAL,
                Custo_Horas_Extras REAL,
                Faltas REAL,
                Abonos REAL,
                Salário REAL,
                Valor_Hora_Extra REAL
            )
        """)
        
        # Adicionar colunas se não existirem (para tabelas já criadas)
        try:
            cursor.execute("ALTER TABLE absenteísmo ADD COLUMN Salário REAL")
        except sqlite3.OperationalError:
            pass  # Coluna já existe
        
        try:
            cursor.execute("ALTER TABLE absenteísmo ADD COLUMN Valor_Hora_Extra REAL")
        except sqlite3.OperationalError:
            pass  # Coluna já existe
        
        conn.commit()
        
        resultados = []
        for registro in dados_extraidos:
            # Verificar se já existe registro para este colaborador/mês/ano
            cursor.execute("""
                SELECT rowid FROM absenteísmo 
                WHERE CPF = ? AND Mês = ? AND Ano = ?
            """, (registro.get('cpf'), registro.get('mes'), registro.get('ano')))
            
            existing = cursor.fetchone()
            
            if existing:
                # Atualizar
                cursor.execute("""
                    UPDATE absenteísmo 
                    SET Horas_Extras = ?, Custo_Horas_Extras = ?, Faltas = ?, Abonos = ?, Salário = ?, Valor_Hora_Extra = ?
                    WHERE rowid = ?
                """, (
                    registro.get('horas_extras', 0),
                    registro.get('custo_horas_extras', 0),
                    registro.get('faltas', 0),
                    registro.get('abonos', 0),
                    registro.get('salario', 0),
                    registro.get('valor_hora_extra', 0),
                    existing[0]
                ))
                resultados.append({
                    "status": "atualizado", 
                    "cpf": registro.get('cpf'),
                    "nome": registro.get('nome'),
                    "salario": registro.get('salario', 0),
                    "horas_extras": registro.get('horas_extras', 0),
                    "custo": registro.get('custo_horas_extras', 0)
                })
            else:
                # Inserir novo
                cursor.execute("""
                    INSERT INTO absenteísmo (CPF, Nome, Mês, Ano, Horas_Extras, Custo_Horas_Extras, Faltas, Abonos, Salário, Valor_Hora_Extra)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    registro.get('cpf'),
                    registro.get('nome'),
                    registro.get('mes'),
                    registro.get('ano'),
                    registro.get('horas_extras', 0),
                    registro.get('custo_horas_extras', 0),
                    registro.get('faltas', 0),
                    registro.get('abonos', 0),
                    registro.get('salario', 0),
                    registro.get('valor_hora_extra', 0)
                ))
                resultados.append({
                    "status": "inserido", 
                    "cpf": registro.get('cpf'),
                    "nome": registro.get('nome'),
                    "salario": registro.get('salario', 0),
                    "horas_extras": registro.get('horas_extras', 0),
                    "custo": registro.get('custo_horas_extras', 0)
                })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": f"Processado com sucesso: {len(resultados)} registro(s)",
            "resultados": resultados,
            "dados_extraidos": dados_extraidos
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": f"Erro ao processar PDF: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500

def extrair_dados_folha_ponto(pdf_path):
    """Extrai dados de absenteísmo, horas extras e custos de um PDF de folha de ponto"""
    dados = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                # Extrair informações do colaborador
                cpf_match = re.search(r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})', text)
                nome_match = re.search(r'Empregado:\s*([^\n]+)', text)
                periodo_match = re.search(r'Período:\s*(\d{2}/\d{2}/\d{4})\s*à\s*(\d{2}/\d{2}/\d{4})', text)
                
                if not (cpf_match and nome_match and periodo_match):
                    continue
                
                cpf = cpf_match.group(1).replace('.', '').replace('-', '')
                nome = nome_match.group(1).strip()
                data_inicio = periodo_match.group(1)
                data_fim = periodo_match.group(2)
                
                # Extrair mês e ano do período
                try:
                    dt_fim = datetime.strptime(data_fim, '%d/%m/%Y')
                    mes = dt_fim.strftime('%B')  # Nome do mês em inglês
                    # Converter para português
                    meses_pt = {
                        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
                        'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
                        'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
                        'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
                    }
                    mes = meses_pt.get(mes, mes)
                    ano = dt_fim.year
                except:
                    continue
                
                # Extrair totais de horas extras
                # Procurar por padrões como "TOTALS" ou "Total" seguido de horas
                horas_extras = 0
                faltas = 0
                abonos = 0
                
                # Procurar por totais na tabela
                totals_match = re.search(r'TOTALS.*?(\d{1,2}):(\d{2})', text, re.DOTALL)
                if totals_match:
                    horas = int(totals_match.group(1))
                    minutos = int(totals_match.group(2))
                    horas_extras = horas + (minutos / 60)
                
                # Procurar por faltas (linhas com "Faltantes")
                faltas_match = re.findall(r'Faltantes.*?(\d{1,2}):(\d{2})', text)
                if faltas_match:
                    for f in faltas_match:
                        faltas += int(f[0]) + (int(f[1]) / 60)
                
                # Procurar por abonos (linhas com "Abonadas")
                abonos_match = re.findall(r'Abonadas.*?(\d{1,2}):(\d{2})', text)
                if abonos_match:
                    for a in abonos_match:
                        abonos += int(a[0]) + (int(a[1]) / 60)
                
                # Buscar salário do colaborador no banco
                conn_temp = get_db_connection()
                cursor_temp = conn_temp.cursor()
                
                # Tentar encontrar colaborador por CPF (com ou sem formatação)
                cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
                cursor_temp.execute("""
                    SELECT Salário, "Salário", salário, "Salario", salario 
                    FROM colaboradores 
                    WHERE CPF = ? OR CPF = ? OR REPLACE(REPLACE(REPLACE(CPF, '.', ''), '-', ''), ' ', '') = ?
                """, (cpf, cpf_formatado, cpf))
                
                salario_result = cursor_temp.fetchone()
                salario = 0
                
                if salario_result:
                    # Tentar encontrar o primeiro valor não nulo
                    for val in salario_result:
                        if val is not None:
                            try:
                                salario = float(val)
                                break
                            except (ValueError, TypeError):
                                continue
                
                conn_temp.close()
                
                # Calcular valor da hora extra baseado no salário
                # Assumindo 220 horas/mês (44h semanais * 5 semanas)
                horas_mes = 220
                valor_hora_normal = salario / horas_mes if horas_mes > 0 else 0
                # Hora extra = 50% adicional (1.5x) ou 100% (2x) dependendo do caso
                # Usando 1.5x como padrão (50% adicional)
                valor_hora_extra = valor_hora_normal * 1.5
                custo_horas_extras = horas_extras * valor_hora_extra
                
                dados.append({
                    'cpf': cpf,
                    'nome': nome,
                    'mes': mes,
                    'ano': ano,
                    'horas_extras': round(horas_extras, 2),
                    'custo_horas_extras': round(custo_horas_extras, 2),
                    'faltas': round(faltas, 2),
                    'abonos': round(abonos, 2),
                    'salario': salario,
                    'valor_hora_extra': round(valor_hora_extra, 2)
                })
    
    except Exception as e:
        raise Exception(f"Erro ao extrair dados do PDF: {str(e)}")
    
    return dados

@app.route('/api/upload/folha-iob', methods=['POST'])
def upload_folha_iob():
    """Processa PDF da folha IOB e extrai dados financeiros"""
    print("\n" + "="*80)
    print("UPLOAD FOLHA IOB - INICIANDO")
    print("="*80)
    
    if not PDF_AVAILABLE:
        print("ERRO: pdfplumber não está instalado")
        return jsonify({"error": "Biblioteca pdfplumber não está instalada"}), 500
    
    if 'file' not in request.files:
        print("ERRO: Nenhum arquivo enviado")
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '':
        print("ERRO: Nome de arquivo vazio")
        return jsonify({"error": "Nome de arquivo vazio"}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        print("ERRO: Arquivo não é PDF")
        return jsonify({"error": "Arquivo deve ser PDF"}), 400
    
    print(f"Arquivo recebido: {file.filename}")
    print(f"Tamanho do arquivo: {file.content_length} bytes")
    
    try:
        # Salvar arquivo temporariamente
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        print(f"Arquivo salvo temporariamente em: {tmp_path}")
        
        # Extrair dados do PDF
        print("Chamando função extrair_dados_folha_iob...")
        dados_extraidos = extrair_dados_folha_iob(tmp_path)
        print(f"Dados extraídos: {len(dados_extraidos)} registros")
        for d in dados_extraidos:
            print(f"  - {d}")
        
        # Limpar arquivo temporário
        os.unlink(tmp_path)
        
        # Validar dados extraídos
        if not dados_extraidos:
            return jsonify({
                "error": "Nenhum dado foi extraído do PDF",
                "message": "Verifique se o formato do PDF está correto ou se contém os dados esperados"
            }), 400
        
        # Inserir dados no banco (base_kpi)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        resultados = []
        for registro in dados_extraidos:
            # Verificar se já existe registro para este KPI/mês/ano
            cursor.execute("""
                SELECT rowid FROM base_kpi 
                WHERE KPI = ? AND Mês = ? AND Ano = ?
            """, (registro.get('kpi'), registro.get('mes'), registro.get('ano')))
            
            existing = cursor.fetchone()
            
            if existing:
                # Atualizar
                cursor.execute("""
                    UPDATE base_kpi 
                    SET Valor = ?
                    WHERE rowid = ?
                """, (registro.get('valor'), existing[0]))
                resultados.append({"status": "atualizado", "kpi": registro.get('kpi')})
            else:
                # Inserir novo
                cursor.execute("""
                    INSERT INTO base_kpi (KPI, Mês, Ano, Valor, Tipo)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    registro.get('kpi'),
                    registro.get('mes'),
                    registro.get('ano'),
                    registro.get('valor'),
                    registro.get('tipo', 'Folha')
                ))
                resultados.append({"status": "inserido", "kpi": registro.get('kpi')})
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": f"Processado com sucesso: {len(resultados)} registro(s)",
            "resultados": resultados,
            "dados_extraidos": dados_extraidos
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": f"Erro ao processar PDF: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500

def extrair_dados_folha_iob(pdf_path):
    """Extrai dados financeiros de um PDF da folha IOB no formato específico"""
    import sys
    sys.stdout.flush()  # Forçar flush do buffer
    
    dados = []
    
    print(f"\n{'='*80}")
    print("FUNÇÃO extrair_dados_folha_iob CHAMADA")
    print(f"{'='*80}")
    print(f"PDF path: {pdf_path}")
    
    try:
        print("Abrindo PDF...")
        with pdfplumber.open(pdf_path) as pdf:
            print(f"PDF aberto! Total de páginas: {len(pdf.pages)}")
            sys.stdout.flush()
            
            text_completo = ""
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\nProcessando página {page_num}/{len(pdf.pages)}...")
                sys.stdout.flush()
                page_text = page.extract_text()
                if page_text:
                    text_completo += page_text + "\n"
                    print(f"PÁGINA {page_num} - {len(page_text)} caracteres extraídos")
                    print("-" * 80)
                    # Mostrar primeiros 1000 caracteres
                    preview = page_text[:1000] + "..." if len(page_text) > 1000 else page_text
                    print(preview)
                    print("-" * 80)
                else:
                    print(f"PÁGINA {page_num}: SEM TEXTO EXTRAÍDO!")
                sys.stdout.flush()
            
            print(f"\n{'='*80}")
            print("TEXTO COMPLETO EXTRAÍDO:")
            print(f"{'='*80}")
            print(text_completo)
            print(f"{'='*80}")
            print(f"Total de caracteres: {len(text_completo)}")
            print(f"{'='*80}\n")
            sys.stdout.flush()
            
            # Extrair período (mês/ano) do cabeçalho
            # Padrão: "Mês/Ano: 01/2025" ou "Relação do Pagamento Mensal Mês/Ano: 01/2025"
            periodo_match = re.search(r'Mês/Ano:\s*(\d{2})/(\d{4})', text_completo, re.IGNORECASE)
            if not periodo_match:
                periodo_match = re.search(r'Relação do Pagamento Mensal.*?(\d{2})/(\d{4})', text_completo, re.IGNORECASE | re.DOTALL)
            
            if periodo_match:
                mes_num = int(periodo_match.group(1))
                ano = int(periodo_match.group(2))
                meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
                mes = meses[mes_num - 1] if 1 <= mes_num <= 12 else 'Janeiro'
                print(f"DEBUG: Período extraído: {mes}/{ano}")
            else:
                # Tentar padrão alternativo
                periodo_match = re.search(r'(\d{2})/(\d{4})', text_completo)
                if periodo_match:
                    mes_num = int(periodo_match.group(1))
                    ano = int(periodo_match.group(2))
                    meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
                    mes = meses[mes_num - 1] if 1 <= mes_num <= 12 else 'Janeiro'
                    print(f"DEBUG: Período extraído (alternativo): {mes}/{ano}")
                else:
                    mes = 'Janeiro'
                    ano = datetime.now().year
                    print(f"DEBUG: Período não encontrado, usando padrão: {mes}/{ano}")
            
            # Inicializar totais agregados
            total_vencimentos = 0.0
            total_descontos = 0.0
            total_liquido = 0.0
            total_fgts = 0.0
            total_salario_base = 0.0
            total_encargos_inss = 0.0
            total_encargos_irrf = 0.0
            
            # Encontrar todos os blocos de funcionário usando regex mais flexível
            # Padrão: "Funcionário: 126 - AGNALDO MACEDO COSTA" ou "Funcionário: 220 - ALAN..."
            funcionarios_pattern = r'Funcionário:\s*\d+\s*-\s*([A-ZÁÉÍÓÚÇÃÕÊÔ\s]+?)(?=Funcionário:|Total|$)'
            funcionarios_matches = list(re.finditer(funcionarios_pattern, text_completo, re.IGNORECASE | re.MULTILINE))
            
            print(f"DEBUG: Encontrados {len(funcionarios_matches)} funcionários")
            
            # Se não encontrou com o padrão acima, tentar dividir por "Funcionário:"
            if len(funcionarios_matches) == 0:
                # Dividir por "Funcionário:" e processar cada bloco
                partes = re.split(r'Funcionário:\s*\d+\s*-\s*', text_completo)
                print(f"DEBUG: Dividido em {len(partes)} partes")
                
                for i, parte in enumerate(partes[1:], 1):  # Pular primeira parte (cabeçalho)
                    func_text = parte
                    if not func_text.strip():
                        continue
                    
                    # Extrair nome (primeira linha até encontrar "Adm:" ou quebra de linha)
                    nome_match = re.search(r'^([A-ZÁÉÍÓÚÇÃÕÊÔ\s]+?)(?:\s+Adm:|$)', func_text, re.MULTILINE)
                    nome = nome_match.group(1).strip() if nome_match else f"Funcionário {i}"
                    
                    # Extrair valores usando regex mais flexível
                    # Salário Base
                    salario_base_match = re.search(r'Salário Base:\s*([\d.,]+)', func_text, re.IGNORECASE)
                    if salario_base_match:
                        salario_base_str = salario_base_match.group(1).replace('.', '').replace(',', '.')
                        try:
                            salario_base = float(salario_base_str)
                            total_salario_base += salario_base
                            print(f"DEBUG: {nome} - Salário Base: {salario_base}")
                        except ValueError:
                            pass
                    
                    # Total de Vencimentos
                    vencimentos_match = re.search(r'Total de Vencimentos:\s*([\d.,]+)', func_text, re.IGNORECASE)
                    if vencimentos_match:
                        vencimentos_str = vencimentos_match.group(1).replace('.', '').replace(',', '.')
                        try:
                            vencimentos = float(vencimentos_str)
                            total_vencimentos += vencimentos
                            print(f"DEBUG: {nome} - Vencimentos: {vencimentos}")
                        except ValueError:
                            pass
                    
                    # Total de Descontos
                    descontos_match = re.search(r'Total de Descontos:\s*([\d.,]+)', func_text, re.IGNORECASE)
                    if descontos_match:
                        descontos_str = descontos_match.group(1).replace('.', '').replace(',', '.')
                        try:
                            descontos = float(descontos_str)
                            total_descontos += descontos
                            print(f"DEBUG: {nome} - Descontos: {descontos}")
                        except ValueError:
                            pass
                    
                    # Líquido a Receber
                    liquido_match = re.search(r'Líquido a Receber:\s*([\d.,]+)', func_text, re.IGNORECASE)
                    if liquido_match:
                        liquido_str = liquido_match.group(1).replace('.', '').replace(',', '.')
                        try:
                            liquido = float(liquido_str)
                            total_liquido += liquido
                            print(f"DEBUG: {nome} - Líquido: {liquido}")
                        except ValueError:
                            pass
                    
                    # Valor do FGTS
                    fgts_match = re.search(r'Valor do FGTS:\s*([\d.,]+)', func_text, re.IGNORECASE)
                    if fgts_match:
                        fgts_str = fgts_match.group(1).replace('.', '').replace(',', '.')
                        try:
                            fgts = float(fgts_str)
                            total_fgts += fgts
                            print(f"DEBUG: {nome} - FGTS: {fgts}")
                        except ValueError:
                            pass
                    
                    # Desconto INSS - padrão: "00080 DESCONTO INSS 8,7200% 283,40"
                    # Procurar por "DESCONTO INSS" seguido de porcentagem e depois valor
                    inss_patterns = [
                        r'DESCONTO INSS[^\d]*[\d.,]+\%[^\d]*([\d.,]+)',  # Com porcentagem
                        r'DESCONTO INSS[^\d]+([\d.,]+)',  # Sem porcentagem explícita
                    ]
                    for pattern in inss_patterns:
                        inss_match = re.search(pattern, func_text, re.IGNORECASE)
                        if inss_match:
                            inss_str = inss_match.group(1).replace('.', '').replace(',', '.')
                            try:
                                inss = float(inss_str)
                                total_encargos_inss += inss
                                print(f"DEBUG: {nome} - INSS: {inss}")
                                break
                            except ValueError:
                                continue
                    
                    # Desconto IRRF - padrão: "00081 DESCONTO I.R.R.F. 7,50% 31,95"
                    # Pode estar como "DESCONTO I.R.R.F." ou "DESCONTO IRRF"
                    irrf_patterns = [
                        r'DESCONTO I\.?R\.?R\.?F\.?[^\d]*[\d.,]+\%[^\d]*([\d.,]+)',  # Com porcentagem e pontos
                        r'DESCONTO I\.?R\.?R\.?F\.?[^\d]+([\d.,]+)',  # Sem porcentagem explícita
                    ]
                    for pattern in irrf_patterns:
                        irrf_match = re.search(pattern, func_text, re.IGNORECASE)
                        if irrf_match:
                            irrf_str = irrf_match.group(1).replace('.', '').replace(',', '.')
                            try:
                                irrf = float(irrf_str)
                                total_encargos_irrf += irrf
                                print(f"DEBUG: {nome} - IRRF: {irrf}")
                                break
                            except ValueError:
                                continue
            else:
                # Processar usando matches encontrados
                for match in funcionarios_matches:
                    nome = match.group(1).strip()
                    # Pegar texto após o nome até o próximo funcionário
                    start_pos = match.end()
                    next_match = funcionarios_matches[funcionarios_matches.index(match) + 1] if funcionarios_matches.index(match) + 1 < len(funcionarios_matches) else None
                    end_pos = next_match.start() if next_match else len(text_completo)
                    func_text = text_completo[start_pos:end_pos]
                    
                    # Mesma lógica de extração acima...
                    # (código similar ao bloco acima)
            
            print(f"DEBUG: Totais - Vencimentos: {total_vencimentos}, Descontos: {total_descontos}, Líquido: {total_liquido}, FGTS: {total_fgts}")
            
            # Criar registros agregados para base_kpi
            if total_vencimentos > 0:
                dados.append({
                    'kpi': 'Folha de pagamento',
                    'mes': mes,
                    'ano': ano,
                    'valor': total_vencimentos,
                    'tipo': 'Folha'
                })
            
            if total_salario_base > 0:
                dados.append({
                    'kpi': 'Salário Base Total',
                    'mes': mes,
                    'ano': ano,
                    'valor': total_salario_base,
                    'tipo': 'Folha'
                })
            
            if total_descontos > 0:
                dados.append({
                    'kpi': 'Descontos Total',
                    'mes': mes,
                    'ano': ano,
                    'valor': total_descontos,
                    'tipo': 'Folha'
                })
            
            if total_liquido > 0:
                dados.append({
                    'kpi': 'Líquido Total',
                    'mes': mes,
                    'ano': ano,
                    'valor': total_liquido,
                    'tipo': 'Folha'
                })
            
            if total_fgts > 0:
                dados.append({
                    'kpi': 'Encargos FGTS',
                    'mes': mes,
                    'ano': ano,
                    'valor': total_fgts,
                    'tipo': 'Folha'
                })
            
            if total_encargos_inss > 0:
                dados.append({
                    'kpi': 'Encargos INSS',
                    'mes': mes,
                    'ano': ano,
                    'valor': total_encargos_inss,
                    'tipo': 'Folha'
                })
            
            if total_encargos_irrf > 0:
                dados.append({
                    'kpi': 'Encargos IRRF',
                    'mes': mes,
                    'ano': ano,
                    'valor': total_encargos_irrf,
                    'tipo': 'Folha'
                })
            
            # Calcular encargos totais (FGTS + INSS + IRRF)
            encargos_total = total_fgts + total_encargos_inss + total_encargos_irrf
            if encargos_total > 0:
                dados.append({
                    'kpi': 'Encargos',
                    'mes': mes,
                    'ano': ano,
                    'valor': encargos_total,
                    'tipo': 'Folha'
                })
            
            print(f"DEBUG: Total de registros criados: {len(dados)}")
    
    except Exception as e:
        import traceback
        print(f"DEBUG: Erro na extração: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise Exception(f"Erro ao extrair dados do PDF IOB: {str(e)}")
    
    return dados

@app.route('/api/avaliacoes/criar', methods=['POST'])
def criar_avaliacao():
    """Cria uma nova avaliação e retorna um link único"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
        
        # Validar campos obrigatórios
        colaborador_id = data.get('colaborador_id')
        colaborador_nome = data.get('colaborador_nome')
        gestor_nome = data.get('gestor_nome')
        gestor_email = data.get('gestor_email')
        periodo = data.get('periodo', f"{datetime.now().strftime('%B')}/{datetime.now().year}")
        
        if not colaborador_id or not colaborador_nome or not gestor_nome:
            return jsonify({"error": "Campos obrigatórios: colaborador_id, colaborador_nome, gestor_nome"}), 400
        
        # Gerar token único
        import secrets
        token = secrets.token_urlsafe(32)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Criar tabela se não existir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS avaliacoes (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                colaborador_id TEXT,
                colaborador_nome TEXT,
                gestor_nome TEXT,
                gestor_email TEXT,
                periodo TEXT,
                data_criacao TEXT,
                data_preenchimento TEXT,
                status TEXT DEFAULT 'pendente',
                Assiduidade REAL,
                Segurança REAL,
                Produtividade REAL,
                Disciplina REAL,
                Trabalho_em_equipe REAL,
                Colaboração REAL,
                Avaliação_do_Funcionário REAL,
                Pontos_de_Melhoria TEXT,
                Observações TEXT
            )
        """)
        
        # Inserir avaliação
        data_criacao = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO avaliacoes 
            (token, colaborador_id, colaborador_nome, gestor_nome, gestor_email, periodo, data_criacao, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pendente')
        """, (token, colaborador_id, colaborador_nome, gestor_nome, gestor_email, periodo, data_criacao))
        
        conn.commit()
        conn.close()
        
        # Gerar URL do link
        base_url = request.host_url.rstrip('/')
        link_avaliacao = f"{base_url}/avaliacao/{token}"
        
        return jsonify({
            "message": "Avaliação criada com sucesso",
            "token": token,
            "link": link_avaliacao,
            "data_criacao": data_criacao
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/avaliacoes/<token>', methods=['GET'])
def obter_avaliacao(token):
    """Obtém dados de uma avaliação pelo token"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM avaliacoes WHERE token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Avaliação não encontrada"}), 404
        
        avaliacao = row_to_dict(row)
        return jsonify(avaliacao), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/avaliacoes/<token>', methods=['PUT'])
def salvar_avaliacao(token):
    """Salva/atualiza uma avaliação preenchida"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se a avaliação existe
        cursor.execute("SELECT rowid FROM avaliacoes WHERE token = ?", (token,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Avaliação não encontrada"}), 404
        
        # Atualizar avaliação
        data_preenchimento = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE avaliacoes SET
                Assiduidade = ?,
                Segurança = ?,
                Produtividade = ?,
                Disciplina = ?,
                Trabalho_em_equipe = ?,
                Colaboração = ?,
                Avaliação_do_Funcionário = ?,
                Pontos_de_Melhoria = ?,
                Observações = ?,
                data_preenchimento = ?,
                status = 'concluida'
            WHERE token = ?
        """, (
            data.get('Assiduidade'),
            data.get('Segurança'),
            data.get('Produtividade'),
            data.get('Disciplina'),
            data.get('Trabalho_em_equipe'),
            data.get('Colaboração'),
            data.get('Avaliação_do_Funcionário'),
            data.get('Pontos_de_Melhoria', ''),
            data.get('Observações', ''),
            data_preenchimento,
            token
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Avaliação salva com sucesso",
            "status": "concluida"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/avaliacoes', methods=['GET'])
def listar_avaliacoes():
    """Lista todas as avaliações (com filtros opcionais)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Filtros opcionais
        status = request.args.get('status')
        gestor_email = request.args.get('gestor_email')
        
        query = "SELECT * FROM avaliacoes WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if gestor_email:
            query += " AND gestor_email = ?"
            params.append(gestor_email)
        
        query += " ORDER BY data_criacao DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        avaliacoes = [row_to_dict(row) for row in rows]
        
        return jsonify({
            "count": len(avaliacoes),
            "data": avaliacoes
        }), 200
        
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
