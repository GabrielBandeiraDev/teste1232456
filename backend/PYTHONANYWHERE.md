# Configuração para PythonAnywhere

## Passos para Deploy

### 1. Upload dos Arquivos

Faça upload de todos os arquivos do backend para:
```
/home/seu_usuario/mysite/teste1232456/backend/
```

### 2. Configurar o Banco de Dados

No console do PythonAnywhere, execute:
```bash
cd ~/mysite/teste1232456/backend
python import_excel_to_db.py
```

Certifique-se de que o arquivo `template_padrao (1).xlsx` está no diretório correto.

### 3. Configurar WSGI

No painel do PythonAnywhere, vá em **Web** → **WSGI configuration file** e configure:

```python
import sys
path = '/home/seu_usuario/mysite/teste1232456/backend'
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application
```

**IMPORTANTE**: Substitua `seu_usuario` pelo seu nome de usuário do PythonAnywhere!

### 4. Configurar Caminho do Banco de Dados

Edite o arquivo `wsgi.py` e ajuste o caminho se necessário:
```python
path = '/home/SEU_USUARIO/mysite/teste1232456/backend'
```

### 5. Instalar Dependências

No console do PythonAnywhere:
```bash
cd ~/mysite/teste1232456/backend
pip3.10 install --user flask flask-cors pandas openpyxl
```

### 6. Testar Localmente (Console)

Para testar no console do PythonAnywhere:
```bash
cd ~/mysite/teste1232456/backend
python3.10 app.py
```

Se der erro de porta, use:
```bash
PORT=8080 python3.10 app.py
```

### 7. Configurar CORS (se necessário)

Se o frontend estiver em outro domínio, ajuste o CORS no `app.py`:
```python
CORS(app, resources={r"/api/*": {"origins": ["https://seu-dominio.com"]}})
```

### 8. Reload da Aplicação

Após fazer alterações, clique em **Reload** no painel do PythonAnywhere.

## Estrutura de Diretórios Esperada

```
/home/seu_usuario/mysite/teste1232456/
├── backend/
│   ├── app.py
│   ├── wsgi.py
│   ├── import_excel_to_db.py
│   ├── requirements.txt
│   ├── database.db
│   └── template_padrao (1).xlsx (opcional, se ainda precisar importar)
```

## Troubleshooting

### Erro: "Port 5000 is in use"
- No PythonAnywhere, não use `python app.py` diretamente
- Use o WSGI através do painel Web
- Para testes no console, use uma porta diferente: `PORT=8080 python app.py`

### Erro: "Database not found"
- Verifique o caminho do banco no `app.py`
- Execute `python import_excel_to_db.py` novamente
- Verifique permissões do arquivo `database.db`

### Erro: "Module not found"
- Instale as dependências: `pip3.10 install --user -r requirements.txt`
- Verifique se está usando Python 3.10 no PythonAnywhere
