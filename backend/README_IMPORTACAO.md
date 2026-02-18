# 📊 Guia de Importação de Dados

Este guia explica como importar dados do Excel e validar o funcionamento do import de PDFs.

## 📋 Importação do Excel

### ⚠️ IMPORTANTE: Duas Versões Disponíveis

#### 1. **Versão Segura** (Recomendada) - `import_excel_to_db_safe.py`
- ✅ **Preserva dados financeiros existentes** (`base_kpi`)
- ✅ **Preserva dados de absenteísmo** (`absenteísmo`)
- ✅ **Preserva avaliações** (`avaliacoes`)
- ✅ Importa todas as outras tabelas normalmente
- ✅ Ideal para quando você já tem dados no sistema

**Uso:**
```bash
cd backend
python import_excel_to_db_safe.py
```

#### 2. **Versão Original** - `import_excel_to_db.py`
- ⚠️ **Sobrescreve TODAS as tabelas**
- ⚠️ Pode apagar dados financeiros existentes
- ⚠️ Use apenas se quiser recriar tudo do zero

**Uso:**
```bash
cd backend
python import_excel_to_db.py
```

### 📁 Arquivo Excel

O arquivo `template_padrao (1).xlsx` deve estar no diretório `backend/`

### 🔒 Tabelas Protegidas (versão segura)

As seguintes tabelas **NÃO serão sobrescritas** se já tiverem dados:
- `base_kpi` - Dados financeiros (folha, encargos, etc.)
- `absenteísmo` - Dados de absenteísmo e horas extras
- `avaliacoes` - Avaliações de desempenho criadas

### 📝 Exemplo de Saída (versão segura)

```
📊 Importação Segura do Excel
Arquivo: backend/template_padrao (1).xlsx
Banco: backend/database.db

📋 Encontradas 5 planilhas: ['Colaboradores', 'Base KPI', 'Dashboard', ...]

📄 Processando: Colaboradores
  - Linhas: 150
  - Colunas: ['Nome', 'CPF', 'Função', ...]
  ✅ Tabela 'colaboradores' importada com sucesso!

📄 Processando: Base KPI
  ⚠️  TABELA PROTEGIDA: 'base_kpi' já possui dados
     Pulando importação para preservar dados existentes

============================================================
✅ Importação concluída!
============================================================
📊 Tabelas importadas: 4
   ✓ colaboradores
   ✓ base_dashboard
   ✓ radar_de_competencias
   ✓ outras_tabelas

⚠️  Tabelas puladas (protegidas): 1
   ⏭️  base_kpi - Dados existentes preservados
```

## 🧪 Validação de Import de PDFs

### Testar Import de Folha de Ponto

```bash
cd backend
python test_pdf_import.py
```

Este script:
- ✅ Testa extração de dados de folhas de ponto
- ✅ Testa extração de dados de folhas IOB
- ✅ Mostra os dados extraídos
- ✅ Valida se o formato está correto

### 📄 Endpoints de Upload

#### 1. Upload Folha de Ponto
- **Endpoint:** `POST /api/upload/folha-ponto`
- **Arquivo:** PDF de folha de ponto
- **Extrai:**
  - CPF e Nome do colaborador
  - Período (mês/ano)
  - Horas Extras
  - Faltas
  - Abonos
  - Custo calculado
- **Salva em:** Tabela `absenteísmo`

#### 2. Upload Folha IOB
- **Endpoint:** `POST /api/upload/folha-iob`
- **Arquivo:** PDF de folha mensal IOB
- **Extrai:**
  - Folha de Pagamento Total
  - Salário Base Total
  - Descontos Total
  - Líquido Total
  - Encargos (FGTS, INSS, IRRF)
- **Salva em:** Tabela `base_kpi`
- **Proteção:** Atualiza apenas se já existir registro para o mesmo KPI/mês/ano

### ✅ Validações Implementadas

1. **Validação de arquivo:**
   - Verifica se é PDF
   - Verifica se arquivo não está vazio
   - Verifica se biblioteca pdfplumber está instalada

2. **Validação de dados extraídos:**
   - Verifica se algum dado foi extraído
   - Retorna erro descritivo se nenhum dado encontrado

3. **Proteção de dados:**
   - Folha IOB: Atualiza apenas registros existentes (mesmo KPI/mês/ano)
   - Folha Ponto: Insere ou atualiza por CPF/mês/ano

### 🔍 Troubleshooting

#### Erro: "Nenhum dado foi extraído do PDF"
- Verifique se o formato do PDF está correto
- Verifique se o PDF contém os campos esperados
- Teste com `python test_pdf_import.py`

#### Erro: "Biblioteca pdfplumber não está instalada"
```bash
pip install pdfplumber
```

#### Dados financeiros foram sobrescritos
- Use `import_excel_to_db_safe.py` na próxima vez
- Os dados de PDFs (via upload) são sempre preservados/atualizados, nunca apagados

## 📊 Estrutura de Dados

### Tabela `base_kpi`
- **Campos:** KPI, Mês, Ano, Valor, Tipo
- **Fonte de dados:**
  - Upload de PDFs IOB (via `/api/upload/folha-iob`)
  - Import do Excel (se tabela estiver vazia)

### Tabela `absenteísmo`
- **Campos:** CPF, Nome, Mês, Ano, Horas_Extras, Custo_Horas_Extras, Faltas, Abonos, Salário
- **Fonte de dados:**
  - Upload de PDFs de folha de ponto (via `/api/upload/folha-ponto`)
  - Import do Excel (se tabela estiver vazia)

## 🚀 Fluxo Recomendado

1. **Primeira vez:**
   ```bash
   python import_excel_to_db_safe.py  # Importa dados iniciais
   ```

2. **Adicionar dados via PDFs:**
   - Use a interface web para fazer upload de PDFs
   - Os dados serão adicionados/atualizados automaticamente

3. **Atualizar dados do Excel:**
   ```bash
   python import_excel_to_db_safe.py  # Preserva dados de PDFs
   ```

4. **Validar import de PDFs:**
   ```bash
   python test_pdf_import.py  # Testa se extração está funcionando
   ```
