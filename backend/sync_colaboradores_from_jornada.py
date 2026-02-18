#!/usr/bin/env python3
"""
Script para sincronizar colaboradores da tabela absenteísmo para a tabela colaboradores.
Adiciona todos os colaboradores que aparecem nos PDFs mas não estão na tabela de colaboradores.
"""
import sqlite3
from pathlib import Path

# Caminho do banco de dados
BASE_DIR = Path(__file__).parent.absolute()
DB_FILE = BASE_DIR / "database.db"

def normalizar_nome(nome: str) -> str:
    """Normaliza nome para comparação (remove espaços extras, maiúsculas)"""
    if not nome:
        return ""
    return " ".join(nome.upper().split())

def sync_colaboradores():
    """Sincroniza colaboradores da tabela absenteísmo para colaboradores"""
    
    if not DB_FILE.exists():
        print(f"❌ Erro: banco não encontrado: {DB_FILE}")
        return 1
    
    print(f"📊 Sincronizando colaboradores de absenteísmo para colaboradores...")
    print(f"   Banco: {DB_FILE}\n")
    
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    
    try:
        # Buscar todos os colaboradores únicos da tabela absenteísmo
        cursor.execute("""
            SELECT DISTINCT 
                Nome,
                Matricula,
                MAX(Salário) as Salario,
                MAX(Ano) as AnoMaisRecente
            FROM absenteísmo
            WHERE Nome IS NOT NULL AND Nome != ''
            GROUP BY Nome, Matricula
            ORDER BY Nome
        """)
        
        colaboradores_absenteismo = cursor.fetchall()
        print(f"📋 Encontrados {len(colaboradores_absenteismo)} colaboradores únicos na tabela absenteísmo\n")
        
        if len(colaboradores_absenteismo) == 0:
            print("⚠️  Nenhum colaborador encontrado na tabela absenteísmo")
            return 0
        
        # Buscar colaboradores existentes na tabela colaboradores
        cursor.execute("SELECT Nome, Matricula, CPF FROM colaboradores")
        colaboradores_existentes = cursor.fetchall()
        
        # Criar mapas para busca rápida
        # Mapa por nome normalizado
        existentes_por_nome = {}
        # Mapa por matrícula
        existentes_por_matricula = {}
        
        for nome, matricula, cpf in colaboradores_existentes:
            if nome:
                nome_norm = normalizar_nome(nome)
                if nome_norm:
                    existentes_por_nome[nome_norm] = (nome, matricula, cpf)
            if matricula:
                existentes_por_matricula[matricula] = (nome, matricula, cpf)
        
        print(f"📋 Encontrados {len(colaboradores_existentes)} colaboradores existentes na tabela colaboradores\n")
        
        # Processar cada colaborador da absenteísmo
        adicionados = 0
        atualizados = 0
        ja_existem = 0
        
        for nome, matricula, salario, ano_mais_recente in colaboradores_absenteismo:
            nome_norm = normalizar_nome(nome) if nome else ""
            
            # Verificar se já existe por nome ou matrícula
            existe = False
            if nome_norm and nome_norm in existentes_por_nome:
                existe = True
            elif matricula and matricula in existentes_por_matricula:
                existe = True
            
            if existe:
                ja_existem += 1
                # Atualizar salário se for mais recente e maior
                if salario and salario > 0:
                    cursor.execute("""
                        UPDATE colaboradores 
                        SET Salário = ?
                        WHERE (Nome = ? OR Matricula = ?)
                        AND (Salário IS NULL OR Salário = 0 OR Salário < ?)
                    """, (salario, nome, matricula, salario))
                    if cursor.rowcount > 0:
                        atualizados += 1
            else:
                # Adicionar novo colaborador
                cursor.execute("""
                    INSERT INTO colaboradores (
                        Nome,
                        "Nome Completo Funcionário",
                        Matricula,
                        Salário,
                        Status,
                        CPF
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    nome,
                    nome,  # Nome Completo Funcionário
                    matricula or "",
                    salario or 0,
                    "Ativo",  # Assumir ativo se está na folha
                    ""  # CPF vazio (não temos nos PDFs)
                ))
                adicionados += 1
                print(f"  ✓ Adicionado: {nome} (Matrícula: {matricula or 'N/A'}, Salário: R$ {salario or 0:,.2f})")
        
        conn.commit()
        
        print(f"\n✅ Sincronização concluída!")
        print(f"   - Adicionados: {adicionados}")
        print(f"   - Atualizados: {atualizados}")
        print(f"   - Já existiam: {ja_existem}")
        print(f"   - Total processados: {len(colaboradores_absenteismo)}")
        
        # Mostrar total de colaboradores agora
        cursor.execute("SELECT COUNT(*) FROM colaboradores")
        total_colaboradores = cursor.fetchone()[0]
        print(f"\n📊 Total de colaboradores na tabela: {total_colaboradores}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao sincronizar: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(sync_colaboradores())
