"""
Script para testar se a API está retornando os dados corretamente
"""
import requests
import json

# URL base da API (ajustar conforme necessário)
BASE_URL = "https://altusengenharia.pythonanywhere.com/api"
# Para teste local: BASE_URL = "http://localhost:5000/api"

def test_api():
    """Testa os endpoints principais da API"""
    
    print("=" * 60)
    print("TESTE DA API - Verificação de Estrutura de Dados")
    print("=" * 60)
    
    # 1. Health check
    print("\n1. Health Check:")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Resposta: {response.json()}")
    except Exception as e:
        print(f"   ERRO: {e}")
    
    # 2. Listar tabelas
    print("\n2. Listar Tabelas:")
    try:
        response = requests.get(f"{BASE_URL}/tables")
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Tabelas encontradas: {len(data.get('tables', []))}")
        print(f"   Tabelas: {data.get('tables', [])}")
    except Exception as e:
        print(f"   ERRO: {e}")
    
    # 3. Buscar dados de base_kpi
    print("\n3. Dados de base_kpi (primeiros 3 registros):")
    try:
        response = requests.get(f"{BASE_URL}/data/base_kpi")
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Estrutura retornada: {list(data.keys())}")
        print(f"   Total de registros: {data.get('count', 0)}")
        
        if data.get('data') and len(data['data']) > 0:
            print(f"\n   Primeiro registro:")
            first_record = data['data'][0]
            print(f"   Chaves: {list(first_record.keys())}")
            print(f"   Exemplo de valores:")
            for key, value in list(first_record.items())[:5]:
                print(f"     {key}: {value} (tipo: {type(value).__name__})")
            
            # Verificar campo de mês
            mes_fields = [k for k in first_record.keys() if 'mês' in k.lower() or 'mes' in k.lower()]
            if mes_fields:
                print(f"\n   Campo de mês encontrado: {mes_fields[0]}")
                print(f"   Valor do mês no primeiro registro: {first_record[mes_fields[0]]}")
                print(f"   Tipo: {type(first_record[mes_fields[0]]).__name__}")
        else:
            print("   Nenhum dado encontrado")
    except Exception as e:
        print(f"   ERRO: {e}")
    
    # 4. Buscar filtros disponíveis
    print("\n4. Filtros disponíveis em base_kpi:")
    try:
        response = requests.get(f"{BASE_URL}/data/base_kpi/filters")
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Meses disponíveis: {data.get('meses', [])}")
        print(f"   Anos disponíveis: {data.get('anos', [])}")
        print(f"   Colunas detectadas: {data.get('columns', {})}")
    except Exception as e:
        print(f"   ERRO: {e}")
    
    # 5. Testar filtro por mês
    print("\n5. Teste de filtro por mês (Janeiro/2025):")
    try:
        response = requests.get(f"{BASE_URL}/data/base_kpi?mes=Janeiro&ano=2025")
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Registros filtrados: {data.get('count', 0)}")
        print(f"   Filtros aplicados: {data.get('filters', {})}")
    except Exception as e:
        print(f"   ERRO: {e}")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
