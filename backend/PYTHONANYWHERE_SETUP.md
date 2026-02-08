# Configuração do Backend no PythonAnywhere

## Passos para Deploy

### 1. Upload dos Arquivos
- Faça upload de todos os arquivos da pasta `backend/` para o PythonAnywhere
- Certifique-se de que o arquivo `database.db` está no mesmo diretório do `app.py`
- O arquivo `wsgi.py` deve estar na raiz do diretório web app

### 2. Instalar Dependências
No console Bash do PythonAnywhere:
```bash
cd ~/mysite
pip3.10 install --user -r backend/requirements.txt
```

### 3. Configurar WSGI
No painel do PythonAnywhere:
1. Vá em **Web** → **Web apps**
2. Selecione ou crie sua aplicação
3. Clique em **WSGI configuration file**
4. Configure para usar o arquivo `wsgi.py`:
```python
# O arquivo wsgi.py já está configurado automaticamente
# Apenas certifique-se de que o caminho está correto
```

### 4. Verificar Caminho do Banco de Dados
O código tenta encontrar o banco de dados automaticamente em:
- `backend/database.db` (diretório atual)
- `../backend/database.db` (diretório pai)
- `~/mysite/backend/database.db` (PythonAnywhere padrão)

### 5. Testar a API
Após configurar, teste os endpoints:
- Health check: `https://seu-usuario.pythonanywhere.com/api/health`
- Listar tabelas: `https://seu-usuario.pythonanywhere.com/api/tables`
- Dados com filtro: `https://seu-usuario.pythonanywhere.com/api/data/base_kpi?mes=Janeiro&ano=2024`
- Filtros disponíveis: `https://seu-usuario.pythonanywhere.com/api/data/base_kpi/filters`

## Endpoints Disponíveis

### GET `/api/health`
Verifica se o backend está funcionando.

### GET `/api/tables`
Lista todas as tabelas disponíveis no banco.

### GET `/api/data/<table_name>`
Retorna todos os dados de uma tabela.
**Parâmetros opcionais:**
- `?mes=Janeiro` - Filtrar por mês
- `?ano=2024` - Filtrar por ano
- `?mes=Janeiro&ano=2024` - Filtrar por mês e ano

### GET `/api/data/<table_name>/filters`
Retorna os meses e anos únicos disponíveis em uma tabela.

### POST `/api/data/<table_name>`
Adiciona novos registros a uma tabela.

### PUT `/api/data/<table_name>/<id>`
Atualiza um registro específico.

### DELETE `/api/data/<table_name>/<id>`
Deleta um registro específico.

### GET `/api/schema/<table_name>`
Retorna a estrutura (schema) de uma tabela.

## Solução de Problemas

### Erro: "Banco de dados não encontrado"
- Verifique se o arquivo `database.db` está no diretório correto
- Verifique os logs do PythonAnywhere para ver qual caminho está sendo tentado
- Certifique-se de que o arquivo tem permissões de leitura

### Erro: "Module not found"
- Certifique-se de que todas as dependências estão instaladas
- Use `pip3.10 install --user` para instalar no ambiente do usuário

### Erro: "Port 5000 is in use"
- No PythonAnywhere, não use `python app.py` diretamente
- Use o arquivo `wsgi.py` através da configuração Web do PythonAnywhere
- Para testes no console, use uma porta diferente: `PORT=8080 python app.py`

## Logs
Os logs do PythonAnywhere podem ser visualizados em:
- **Web** → **Web apps** → **Error log**
- **Tasks** → **Console** (para comandos manuais)
