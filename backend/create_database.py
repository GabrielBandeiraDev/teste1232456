#!/usr/bin/env python3
"""
Script para criar o banco de dados SQLite com as tabelas necessárias
"""
import sqlite3
from pathlib import Path

# Caminho do banco de dados
BASE_DIR = Path(__file__).parent.absolute()
DB_FILE = BASE_DIR / "database.db"

def create_database():
    """Cria o banco de dados com todas as tabelas necessárias"""
    
    print(f"📊 Criando banco de dados em: {DB_FILE}")
    
    # Conectar ao SQLite (cria o arquivo se não existir)
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    
    try:
        # Criar tabela absenteísmo
        print("  ✓ Criando tabela 'absenteísmo'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS absenteísmo (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                CPF TEXT,
                Nome TEXT,
                Matricula TEXT,
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
        
        # Criar tabela base_kpi
        print("  ✓ Criando tabela 'base_kpi'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS base_kpi (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                KPI TEXT,
                Mês TEXT,
                Ano INTEGER,
                Valor REAL,
                Tipo TEXT
            )
        """)
        
        # Criar tabela colaboradores (se não existir)
        print("  ✓ Criando tabela 'colaboradores'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS colaboradores (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                CPF TEXT,
                Nome TEXT,
                "Nome Completo Funcionário" TEXT,
                Matricula TEXT,
                Função TEXT,
                Departamento TEXT,
                Base TEXT,
                Status TEXT,
                Admissão TEXT,
                Salário REAL
            )
        """)
        
        # Criar tabela base_dashboard (se não existir)
        print("  ✓ Criando tabela 'base_dashboard'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS base_dashboard (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                Métrica TEXT,
                Valor REAL,
                Período TEXT
            )
        """)
        
        # Criar tabela radar_de_competencias (se não existir)
        print("  ✓ Criando tabela 'radar_de_competencias'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS radar_de_competencias (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                Colaborador TEXT,
                Competência TEXT,
                Nível REAL,
                Período TEXT
            )
        """)
        
        # Criar tabela avaliacoes (sistema de avaliações por link)
        print("  ✓ Criando tabela 'avaliacoes'...")
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
        
        conn.commit()
        print(f"\n✅ Banco de dados criado com sucesso em: {DB_FILE}")
        
        # Mostrar tabelas criadas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n📋 Tabelas criadas: {[t[0] for t in tables]}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao criar banco de dados: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    create_database()
