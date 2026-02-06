"""
Script para importar dados do Excel template_padrao para SQLite
"""
import pandas as pd
import sqlite3
import os
from pathlib import Path
from datetime import timedelta, datetime
import numpy as np

# Caminhos
# PythonAnywhere: ajustar caminhos conforme necessário
BASE_DIR = Path(__file__).parent
EXCEL_FILE = BASE_DIR / "template_padrao (1).xlsx"
DB_FILE = BASE_DIR / "database.db"

# Se não encontrar no diretório atual, tentar diretório pai
if not EXCEL_FILE.exists():
    EXCEL_FILE = BASE_DIR.parent / "template_padrao (1).xlsx"
if not DB_FILE.exists() and (BASE_DIR.parent / "backend" / "database.db").exists():
    DB_FILE = BASE_DIR.parent / "backend" / "database.db"

def import_excel_to_sqlite():
    """Importa todas as planilhas do Excel para tabelas SQLite"""
    
    print(f"Lendo arquivo Excel: {EXCEL_FILE}")
    
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(f"Arquivo Excel não encontrado: {EXCEL_FILE}")
    
    # Conectar ao SQLite (cria o arquivo se não existir)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Ler todas as planilhas do Excel
        excel_file = pd.ExcelFile(EXCEL_FILE)
        sheet_names = excel_file.sheet_names
        
        print(f"Encontradas {len(sheet_names)} planilhas: {sheet_names}")
        
        for sheet_name in sheet_names:
            print(f"\nProcessando planilha: {sheet_name}")
            
            # Ler dados da planilha
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
            
            # Limpar nome da tabela (remover caracteres especiais)
            table_name = sheet_name.lower().replace(" ", "_").replace("-", "_")
            # Remove caracteres inválidos para nome de tabela
            table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
            
            print(f"  - Linhas: {len(df)}")
            print(f"  - Colunas: {list(df.columns)}")
            
            # Limpar colunas "Unnamed" (geralmente são índices ou cabeçalhos vazios)
            df.columns = [col if not str(col).startswith('Unnamed') else f'col_{i}' 
                         for i, col in enumerate(df.columns)]
            
            # Função auxiliar para converter valores problemáticos
            def convert_for_sqlite(x):
                """Converte valores para tipos suportados pelo SQLite"""
                if pd.isna(x) or x is None:
                    return None
                if isinstance(x, timedelta):
                    # Converter timedelta para segundos (float)
                    return float(x.total_seconds())
                if isinstance(x, (datetime, pd.Timestamp)):
                    return x.isoformat()
                if isinstance(x, (int, float, str, bool)):
                    return x
                # Converter outros tipos para string
                return str(x)
            
            # Converter tipos problemáticos para SQLite
            for col in df.columns:
                try:
                    # Verificar se é timedelta64
                    if str(df[col].dtype) == 'timedelta64[ns]':
                        df[col] = df[col].apply(lambda x: float(x.total_seconds()) if pd.notna(x) else None)
                    # Verificar se é datetime
                    elif pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = df[col].apply(lambda x: x.isoformat() if pd.notna(x) else None)
                    # Para colunas object, verificar e converter valores individuais
                    elif df[col].dtype == 'object':
                        # Aplicar conversão em todos os valores
                        df[col] = df[col].apply(convert_for_sqlite)
                except Exception as e:
                    print(f"    ⚠️  Aviso ao processar coluna '{col}': {e}")
                    # Em caso de erro, tentar converter tudo
                    try:
                        df[col] = df[col].apply(convert_for_sqlite)
                    except:
                        df[col] = df[col].astype(str).replace('nan', None)
            
            # Substituir NaN/NaT por None (NULL no SQL)
            df = df.replace({np.nan: None, pd.NaT: None})
            # Também substituir strings 'nan' e 'NaT'
            df = df.replace({'nan': None, 'NaT': None, 'None': None})
            
            # Criar tabela no SQLite
            # Primeiro, dropa a tabela se existir
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Criar tabela com base no DataFrame
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            print(f"  ✓ Tabela '{table_name}' criada com sucesso!")
        
        conn.commit()
        print(f"\n✓ Importação concluída! Banco de dados criado em: {DB_FILE}")
        
        # Mostrar resumo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nTabelas criadas: {[t[0] for t in tables]}")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao importar: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import_excel_to_sqlite()
