#!/usr/bin/env python3
"""
Script para validar se os dados do Excel estão no SQLite
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
EXCEL_FILE = BASE_DIR / "template_padrao (1).xlsx"
DB_FILE = BASE_DIR / "database.db"

def validar_dados():
    """Valida se os dados do Excel estão no SQLite"""
    
    print("🔍 VALIDAÇÃO: Excel vs SQLite\n")
    print("="*70)
    
    # Verificar arquivos
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
        print(f"\n📋 Planilhas no Excel: {len(sheet_names)}\n")
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
    db_tables.discard('sqlite_sequence')
    
    print(f"📊 Tabelas no banco: {len(db_tables)}\n")
    print("="*70)
    
    # Validar cada planilha
    resultados = []
    total_planilhas = len(sheet_names)
    planilhas_ok = 0
    planilhas_faltando = 0
    planilhas_vazias = 0
    
    for sheet_name in sheet_names:
        # Converter nome da planilha para nome de tabela
        table_name = sheet_name.lower().replace(" ", "_").replace("-", "_")
        table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
        
        # Ler dados do Excel
        try:
            df_excel = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
            linhas_excel = len(df_excel)
        except Exception as e:
            print(f"⚠️  Erro ao ler planilha '{sheet_name}': {e}")
            continue
        
        # Verificar no banco
        if table_name in db_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            linhas_db = cursor.fetchone()[0]
            
            # Comparar
            if linhas_db > 0:
                status = "✅"
                planilhas_ok += 1
                if linhas_excel == linhas_db:
                    comparacao = f"✓ Igual ({linhas_excel} registros)"
                else:
                    comparacao = f"⚠️  Diferente (Excel: {linhas_excel}, DB: {linhas_db})"
            else:
                status = "⚠️  VAZIA"
                planilhas_vazias += 1
                comparacao = f"Tabela existe mas está vazia (Excel tem {linhas_excel} registros)"
        else:
            status = "❌ FALTANDO"
            planilhas_faltando += 1
            comparacao = f"Tabela não existe no banco (Excel tem {linhas_excel} registros)"
        
        resultados.append({
            'planilha': sheet_name,
            'tabela': table_name,
            'status': status,
            'excel': linhas_excel,
            'db': linhas_db if table_name in db_tables else 0,
            'comparacao': comparacao
        })
    
    # Mostrar resultados
    print("\n📊 RESULTADO DA VALIDAÇÃO:\n")
    
    for r in resultados:
        print(f"{r['status']} {r['planilha']}")
        print(f"   → Tabela: {r['tabela']}")
        print(f"   → {r['comparacao']}")
        print()
    
    # Resumo
    print("="*70)
    print("\n📈 RESUMO:\n")
    print(f"  Total de planilhas no Excel: {total_planilhas}")
    print(f"  ✅ Planilhas OK: {planilhas_ok}")
    print(f"  ⚠️  Planilhas vazias no DB: {planilhas_vazias}")
    print(f"  ❌ Planilhas faltando: {planilhas_faltando}")
    
    # Verificar dados específicos
    print("\n" + "="*70)
    print("\n🔍 VALIDAÇÃO DE DADOS ESPECÍFICOS:\n")
    
    # Colaboradores
    if 'colaboradores' in db_tables:
        cursor.execute("SELECT COUNT(*) FROM colaboradores")
        count = cursor.fetchone()[0]
        print(f"  ✓ Colaboradores no banco: {count}")
    
    # Base KPI
    if 'base_kpi' in db_tables:
        cursor.execute("SELECT COUNT(*) FROM base_kpi")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT DISTINCT KPI FROM base_kpi LIMIT 5")
        kpis = [r[0] for r in cursor.fetchall()]
        print(f"  ✓ KPIs no banco: {count}")
        if kpis:
            print(f"    Exemplos: {', '.join(kpis)}")
    
    # Absenteísmo
    if 'absenteísmo' in db_tables:
        cursor.execute("SELECT COUNT(*) FROM absenteísmo")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT Nome) FROM absenteísmo")
        colaboradores_unicos = cursor.fetchone()[0]
        print(f"  ✓ Registros de absenteísmo: {count}")
        print(f"    Colaboradores únicos: {colaboradores_unicos}")
    
    # Radar de Competências
    if 'radar_de_competencias' in db_tables:
        cursor.execute("SELECT COUNT(*) FROM radar_de_competencias")
        count = cursor.fetchone()[0]
        print(f"  ✓ Avaliações de competências: {count}")
    
    # Avaliações (sistema novo)
    if 'avaliacoes' in db_tables:
        cursor.execute("SELECT COUNT(*) FROM avaliacoes")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM avaliacoes WHERE status = 'concluida'")
        concluidas = cursor.fetchone()[0]
        print(f"  ✓ Avaliações criadas: {count}")
        print(f"    Concluídas: {concluidas}")
    
    print("\n" + "="*70)
    
    if planilhas_faltando > 0 or planilhas_vazias > 0:
        print("\n⚠️  AÇÃO RECOMENDADA:")
        print("   Execute: python import_excel_to_db_safe.py")
        print("   para importar as planilhas faltantes")
    else:
        print("\n✅ Todos os dados estão sincronizados!")
    
    conn.close()
    excel_file.close()
    
    return planilhas_faltando == 0 and planilhas_vazias == 0

if __name__ == "__main__":
    sucesso = validar_dados()
    sys.exit(0 if sucesso else 1)
