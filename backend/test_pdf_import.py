"""
Script para testar e validar o import de PDFs
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório atual ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    from app import extrair_dados_folha_ponto, extrair_dados_folha_iob
    PDF_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erro ao importar funções: {e}")
    PDF_AVAILABLE = False

def test_pdf_folha_ponto(pdf_path):
    """Testa extração de dados de folha de ponto"""
    if not PDF_AVAILABLE:
        print("❌ Bibliotecas necessárias não disponíveis")
        return False
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"🧪 Testando extração de Folha de Ponto")
    print(f"{'='*60}")
    print(f"Arquivo: {pdf_path}\n")
    
    try:
        dados = extrair_dados_folha_ponto(pdf_path)
        
        if not dados:
            print("⚠️  Nenhum dado extraído do PDF")
            print("   Verifique se o formato do PDF está correto")
            return False
        
        print(f"✅ Extração bem-sucedida!")
        print(f"   Registros encontrados: {len(dados)}\n")
        
        for i, registro in enumerate(dados, 1):
            print(f"   Registro {i}:")
            print(f"     - CPF: {registro.get('cpf', 'N/A')}")
            print(f"     - Nome: {registro.get('nome', 'N/A')}")
            print(f"     - Período: {registro.get('mes', 'N/A')}/{registro.get('ano', 'N/A')}")
            print(f"     - Horas Extras: {registro.get('horas_extras', 0)}h")
            print(f"     - Custo HE: R$ {registro.get('custo_horas_extras', 0):.2f}")
            print(f"     - Faltas: {registro.get('faltas', 0)}h")
            print(f"     - Abonos: {registro.get('abonos', 0)}h")
            print(f"     - Salário: R$ {registro.get('salario', 0):.2f}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao processar PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pdf_folha_iob(pdf_path):
    """Testa extração de dados de folha IOB"""
    if not PDF_AVAILABLE:
        print("❌ Bibliotecas necessárias não disponíveis")
        return False
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"🧪 Testando extração de Folha IOB")
    print(f"{'='*60}")
    print(f"Arquivo: {pdf_path}\n")
    
    try:
        dados = extrair_dados_folha_iob(pdf_path)
        
        if not dados:
            print("⚠️  Nenhum dado extraído do PDF")
            print("   Verifique se o formato do PDF está correto")
            return False
        
        print(f"✅ Extração bem-sucedida!")
        print(f"   KPIs encontrados: {len(dados)}\n")
        
        for i, registro in enumerate(dados, 1):
            print(f"   KPI {i}:")
            print(f"     - Nome: {registro.get('kpi', 'N/A')}")
            print(f"     - Período: {registro.get('mes', 'N/A')}/{registro.get('ano', 'N/A')}")
            print(f"     - Valor: R$ {registro.get('valor', 0):.2f}")
            print(f"     - Tipo: {registro.get('tipo', 'N/A')}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao processar PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal para testar PDFs"""
    print("🔍 Validação de Importação de PDFs\n")
    
    # Procurar PDFs de exemplo
    pdf_dir = BASE_DIR / "PDF"
    folha_ponto_dir = pdf_dir
    folha_iob_dir = pdf_dir
    
    # Testar folha de ponto
    folha_ponto_files = list(folha_ponto_dir.glob("*.pdf"))
    if folha_ponto_files:
        print(f"📄 Encontrados {len(folha_ponto_files)} PDF(s) para testar")
        # Testar o primeiro PDF encontrado
        test_pdf_folha_ponto(folha_ponto_files[0])
    else:
        print("⚠️  Nenhum PDF de folha de ponto encontrado para testar")
        print(f"   Procurando em: {folha_ponto_dir}")
    
    # Testar folha IOB
    folha_iob_files = [f for f in folha_iob_dir.glob("*.pdf") if "Folha Mensal" in f.name]
    if folha_iob_files:
        print(f"\n📄 Encontrados {len(folha_iob_files)} PDF(s) de folha IOB para testar")
        # Testar o primeiro PDF encontrado
        test_pdf_folha_iob(folha_iob_files[0])
    else:
        print("\n⚠️  Nenhum PDF de folha IOB encontrado para testar")
        print(f"   Procurando em: {folha_iob_dir}")
    
    print(f"\n{'='*60}")
    print("✅ Validação concluída!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
