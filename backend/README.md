# Backend Flask - Altus Engenharia

## Instalação

1. Crie um ambiente virtual (recomendado):
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Importar dados do Excel para SQLite

Execute o script de importação:
```bash
python import_excel_to_db.py
```

Este script irá:
- Ler o arquivo `template_padrao (1).xlsx` da raiz do projeto
- Criar um banco de dados SQLite em `backend/database.db`
- Importar todas as planilhas do Excel como tabelas no SQLite

## Executar o servidor

```bash
python app.py
```

O servidor estará disponível em `http://localhost:5000`

## Endpoints da API

### Health Check
- `GET /api/health` - Verifica se o backend está funcionando

### Listar Tabelas
- `GET /api/tables` - Retorna lista de todas as tabelas disponíveis

### Obter Dados
- `GET /api/data/<table_name>` - Retorna todos os dados de uma tabela específica
- `GET /api/data/all` - Retorna todos os dados de todas as tabelas

### Adicionar Dados
- `POST /api/data/<table_name>` - Adiciona novos registros a uma tabela
  - Body: JSON com os dados (pode ser um objeto ou array de objetos)

### Atualizar Dados
- `PUT /api/data/<table_name>/<record_id>` - Atualiza um registro específico
  - Body: JSON com os campos a atualizar

### Deletar Dados
- `DELETE /api/data/<table_name>/<record_id>` - Deleta um registro específico

### Schema
- `GET /api/schema/<table_name>` - Retorna a estrutura (schema) de uma tabela

## Exemplos de Uso

### Obter todos os dados de uma tabela
```bash
curl http://localhost:5000/api/data/nome_da_tabela
```

### Adicionar um novo registro
```bash
curl -X POST http://localhost:5000/api/data/nome_da_tabela \
  -H "Content-Type: application/json" \
  -d '{"campo1": "valor1", "campo2": "valor2"}'
```

### Adicionar múltiplos registros
```bash
curl -X POST http://localhost:5000/api/data/nome_da_tabela \
  -H "Content-Type: application/json" \
  -d '[{"campo1": "valor1"}, {"campo1": "valor2"}]'
```
