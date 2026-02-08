# Estrutura de Dados - Backend e Frontend

## ✅ Verificação da Estrutura

### Backend → Frontend

#### 1. Endpoint: `GET /api/data/<table_name>`

**Backend retorna:**
```json
{
  "table": "base_kpi",
  "count": 1832,
  "data": [
    {
      "rowid": 1,
      "KPI": "Folha de pagamento",
      "Mês": "2025-01-01T00:00:00",  // ⚠️ Data ISO
      "Ano": 2025,
      "Valor": 150000.00,
      ...
    }
  ],
  "filters": {
    "mes": null,
    "ano": null
  }
}
```

**Frontend processa:**
- `useTableData('base_kpi')` retorna: `{ data: { table, count, data } }`
- `useDashboardData()` acessa: `baseKpi?.data` → array de registros
- Componentes acessam: `baseKpi[0].Mês` → `"2025-01-01T00:00:00"`

**✅ Estrutura está CORRETA**

### 2. Conversão de Datas

**Problema identificado:**
- Campo `Mês` vem como data ISO: `"2025-01-01T00:00:00"`
- Frontend precisa converter para nome do mês: `"Janeiro"`

**Solução implementada:**
- Função `converterParaNomeMes()` no frontend
- Converte datas ISO → nome do mês
- Converte números (1-12) → nome do mês
- Mantém nomes de meses já existentes

**✅ Conversão implementada**

### 3. Filtros por Mês/Ano

**Backend:**
- Endpoint aceita: `?mes=Janeiro&ano=2025`
- Filtra no banco antes de retornar

**Frontend:**
- Filtra no cliente após receber os dados
- Converte datas ISO antes de comparar

**⚠️ Dupla filtragem:**
- Backend filtra se parâmetros forem passados
- Frontend sempre filtra (mesmo sem parâmetros)

**Recomendação:**
- Usar filtro do backend quando possível (mais eficiente)
- Frontend como fallback para conversão de datas

## 📊 Estrutura de Dados por Tabela

### base_kpi
```typescript
{
  rowid: number
  KPI: string
  Mês: string | Date  // ⚠️ Pode vir como data ISO
  Ano: number
  Valor: number
  Tipo?: string
  ...
}
```

### colaboradores
```typescript
{
  rowid: number
  Nome: string
  CPF: string
  Salário: number
  Base: string
  Status: string
  Admissão: string  // Formato: "DD/MM/YYYY" ou ISO
  ...
}
```

### base_dashboard
```typescript
{
  rowid: number
  Métrica: string
  Valor: number
  Data: string | Date
  ...
}
```

## 🔍 Verificações Necessárias

1. ✅ Backend retorna estrutura correta
2. ✅ Frontend acessa dados corretamente
3. ✅ Conversão de datas implementada
4. ⚠️ Verificar se filtros do backend estão funcionando
5. ⚠️ Verificar se todos os campos estão sendo serializados corretamente

## 🧪 Como Testar

Execute o script de teste:
```bash
cd backend
python test_api.py
```

Ou teste manualmente:
```bash
# Health check
curl https://altusengenharia.pythonanywhere.com/api/health

# Dados de base_kpi
curl https://altusengenharia.pythonanywhere.com/api/data/base_kpi

# Filtros disponíveis
curl https://altusengenharia.pythonanywhere.com/api/data/base_kpi/filters

# Filtro por mês/ano
curl "https://altusengenharia.pythonanywhere.com/api/data/base_kpi?mes=Janeiro&ano=2025"
```

## 📝 Notas Importantes

1. **Datas ISO**: O campo `Mês` pode vir como data ISO. O frontend converte automaticamente.

2. **Serialização**: A função `row_to_dict()` no backend garante que todos os tipos sejam serializáveis para JSON.

3. **Filtros**: O backend suporta filtros, mas o frontend também filtra localmente para garantir compatibilidade com datas ISO.

4. **Performance**: Para grandes volumes de dados, considere usar os filtros do backend em vez de filtrar no frontend.
