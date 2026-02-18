#!/usr/bin/env python3
"""
Script para verificar se todos os dados do Excel foram importados
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
EXCEL_FILE = BASE_DIR / "template_padrao (1).xlsx"
DB_FILE = BASE_DIR / "database.db"

def verificar_importacao():
    """Verifica se todas as planilhas do Excel foram importadas"""
    
    print("🔍 Verificando Importação do Excel\n")
    print(f"{'='*60}\n")
    
    # Verificar se arquivos existem
    if not EXCEL_FILE.exists():
        print(f"❌ Arquivo Excel não encontrado: {EXCEL_FILE}")
        return False
    
    if not DB_FILE.exists():
        print(f"❌ Banco de dados não encontrado: {DB_FILE}")
        return False
    
    # Ler planilhas do Excel
    try:
        import pandas as pd
        excel_file = pd.ExcelFile(EXCEL_FILE)
        sheet_names = excel_file.sheet_names
        print(f"📋 Planilhas no Excel: {len(sheet_names)}\n")
    except ImportError:
        print("❌ pandas não está instalado. Instale com: pip install pandas openpyxl")
        return False
    except Exception as e:
        print(f"❌ Erro ao ler Excel: {e}")
        return False
    
    # Conectar ao banco
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Listar tabelas no banco
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    db_tables = {t[0] for t in cursor.fetchall()}
    db_tables.discard('sqlite_sequence')  # Tabela do sistema
    
    print(f"📊 Tabelas no banco de dados: {len(db_tables)}\n")
    
    # Mapear planilhas para nomes de tabelas
    planilhas_importadas = []
    planilhas_faltando = []
    
    for sheet_name in sheet_names:
        # Converter nome da planilha para nome de tabela
        table_name = sheet_name.lower().replace(" ", "_").replace("-", "_")
        table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
        
        # Verificar se existe no banco
        if table_name in db_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            planilhas_importadas.append((sheet_name, table_name, count))
        else:
            planilhas_faltando.append((sheet_name, table_name))
    
    # Mostrar resultados
    print(f"{'='*60}")
    print("✅ PLANILHAS IMPORTADAS:\n")
    if planilhas_importadas:
        for sheet, table, count in planilhas_importadas:
            print(f"  ✓ {sheet}")
            print(f"    → Tabela: {table}")
            print(f"    → Registros: {count}\n")
    else:
        print("  Nenhuma planilha importada encontrada\n")
    
    if planilhas_faltando:
        print(f"{'='*60}")
        print("⚠️  PLANILHAS NÃO IMPORTADAS:\n")
        for sheet, table in planilhas_faltando:
            print(f"  ⚠️  {sheet}")
            print(f"     → Tabela esperada: {table}\n")
    
    # Resumo
    print(f"{'='*60}")
    print("📊 RESUMO:\n")
    print(f"  Planilhas no Excel: {len(sheet_names)}")
    print(f"  Planilhas importadas: {len(planilhas_importadas)}")
    print(f"  Planilhas faltando: {len(planilhas_faltando)}")
    
    if planilhas_faltando:
        print(f"\n⚠️  AÇÃO NECESSÁRIA:")
        print(f"     Execute: python import_excel_to_db_safe.py")
        print(f"     para importar as planilhas faltantes")
    else:
        print(f"\n✅ Todas as planilhas foram importadas!")
    
    conn.close()
    excel_file.close()
    
    return len(planilhas_faltando) == 0

if __name__ == "__main__":
    sucesso = verificar_importacao()
    sys.exit(0 if sucesso else 1)
