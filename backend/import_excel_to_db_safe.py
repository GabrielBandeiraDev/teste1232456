"""
Script para importar dados do Excel template_padrao para SQLite
VERSÃO SEGURA: Não sobrescreve dados financeiros existentes (base_kpi)
"""
import pandas as pd
import sqlite3
import os
from pathlib import Path
from datetime import timedelta, datetime
import numpy as np

# Caminhos
BASE_DIR = Path(__file__).parent
EXCEL_FILE = BASE_DIR / "template_padrao (1).xlsx"
DB_FILE = BASE_DIR / "database.db"

# Se não encontrar no diretório atual, tentar diretório pai
if not EXCEL_FILE.exists():
    EXCEL_FILE = BASE_DIR.parent / "template_padrao (1).xlsx"
if not DB_FILE.exists() and (BASE_DIR.parent / "backend" / "database.db").exists():
    DB_FILE = BASE_DIR.parent / "backend" / "database.db"

# Tabelas que NÃO devem ser sobrescritas se já tiverem dados
TABELAS_PROTEGIDAS = {
    'base_kpi',  # Dados financeiros - não sobrescrever se já tiver dados
    'absenteísmo',  # Dados de absenteísmo - verificar antes de sobrescrever
    'avaliacoes',  # Avaliações criadas - não sobrescrever
}

def verificar_tabela_tem_dados(cursor, table_name):
    """Verifica se uma tabela já tem dados"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        return count > 0
    except sqlite3.OperationalError:
        return False  # Tabela não existe

def import_excel_to_sqlite_safe():
    """Importa planilhas do Excel para SQLite, protegendo dados existentes"""
    
    print(f"📊 Importação Segura do Excel")
    print(f"Arquivo: {EXCEL_FILE}")
    print(f"Banco: {DB_FILE}\n")
    
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(f"Arquivo Excel não encontrado: {EXCEL_FILE}")
    
    # Conectar ao SQLite
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Ler todas as planilhas do Excel
        excel_file = pd.ExcelFile(EXCEL_FILE)
        sheet_names = excel_file.sheet_names
        
        print(f"📋 Encontradas {len(sheet_names)} planilhas: {sheet_names}\n")
        
        tabelas_importadas = []
        tabelas_puladas = []
        tabelas_atualizadas = []
        
        for sheet_name in sheet_names:
            print(f"📄 Processando: {sheet_name}")
            
            # Ler dados da planilha
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
            
            # Limpar nome da tabela
            table_name = sheet_name.lower().replace(" ", "_").replace("-", "_")
            table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
            
            print(f"  - Linhas: {len(df)}")
            print(f"  - Colunas: {list(df.columns)[:5]}...")
            
            # Verificar se é tabela protegida
            if table_name in TABELAS_PROTEGIDAS:
                tem_dados = verificar_tabela_tem_dados(cursor, table_name)
                
                if tem_dados:
                    print(f"  ⚠️  TABELA PROTEGIDA: '{table_name}' já possui dados")
                    print(f"     Pulando importação para preservar dados existentes")
                    print(f"     (Use import_excel_to_db.py se quiser sobrescrever)")
                    tabelas_puladas.append((table_name, "Dados existentes preservados"))
                    continue
                else:
                    print(f"  ✓ Tabela protegida '{table_name}' está vazia, importando...")
                    tabelas_atualizadas.append(table_name)
            
            # Limpar colunas "Unnamed"
            df.columns = [col if not str(col).startswith('Unnamed') else f'col_{i}' 
                         for i, col in enumerate(df.columns)]
            
            # Função auxiliar para converter valores
            def convert_for_sqlite(x):
                if pd.isna(x) or x is None:
                    return None
                if isinstance(x, timedelta):
                    return float(x.total_seconds())
                if isinstance(x, (datetime, pd.Timestamp)):
                    return x.isoformat()
                if isinstance(x, (int, float, str, bool)):
                    return x
                return str(x)
            
            # Converter tipos problemáticos
            for col in df.columns:
                try:
                    if str(df[col].dtype) == 'timedelta64[ns]':
                        df[col] = df[col].apply(lambda x: float(x.total_seconds()) if pd.notna(x) else None)
                    elif pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = df[col].apply(lambda x: x.isoformat() if pd.notna(x) else None)
                    elif df[col].dtype == 'object':
                        df[col] = df[col].apply(convert_for_sqlite)
                except Exception as e:
                    print(f"    ⚠️  Aviso ao processar coluna '{col}': {e}")
                    try:
                        df[col] = df[col].apply(convert_for_sqlite)
                    except:
                        df[col] = df[col].astype(str).replace('nan', None)
            
            # Substituir NaN/NaT por None
            df = df.replace({np.nan: None, pd.NaT: None})
            df = df.replace({'nan': None, 'NaT': None, 'None': None})
            
            # Verificar se tabela existe e tem dados
            tabela_existe = verificar_tabela_tem_dados(cursor, table_name)
            
            if tabela_existe and table_name not in TABELAS_PROTEGIDAS:
                # Para tabelas não protegidas, perguntar ou fazer merge inteligente
                print(f"  ⚠️  Tabela '{table_name}' já existe com dados")
                print(f"     Substituindo dados existentes...")
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Criar/recriar tabela
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            tabelas_importadas.append(table_name)
            print(f"  ✅ Tabela '{table_name}' importada com sucesso!\n")
        
        conn.commit()
        
        # Resumo
        print(f"\n{'='*60}")
        print(f"✅ Importação concluída!")
        print(f"{'='*60}")
        print(f"📊 Tabelas importadas: {len(tabelas_importadas)}")
        for t in tabelas_importadas:
            print(f"   ✓ {t}")
        
        if tabelas_puladas:
            print(f"\n⚠️  Tabelas puladas (protegidas): {len(tabelas_puladas)}")
            for t, motivo in tabelas_puladas:
                print(f"   ⏭️  {t} - {motivo}")
        
        # Mostrar todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print(f"\n📋 Total de tabelas no banco: {len(tables)}")
        print(f"   {', '.join([t[0] for t in tables])}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro ao importar: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import_excel_to_sqlite_safe()
