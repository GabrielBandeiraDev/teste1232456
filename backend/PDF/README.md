# Extração de dados de PDF – Folhas (Adiantamento e Mensal)

Aplicação em Python para extrair texto e tabelas de PDFs de **Folha de Adiantamento** e **Folha Mensal**.

## Instalação

```bash
cd PDF
pip install -r requirements.txt
```

## Processar todos os PDFs da pasta

Com os arquivos das folhas na pasta `PDF`, rode:

```bash
python extrair_todos.py
```

Isso gera a pasta `extraidos/` com um arquivo JSON por PDF (ex.: `Folha_adiantamento_-_01_26.json`, `Folha_Mensal_-_01_26.json`).

Para gerar também CSV (primeira tabela de cada PDF):

```bash
python extrair_todos.py --csv
```

Opções:
- `--pasta /caminho` – pasta onde estão os PDFs (default: pasta atual)
- `--saida nome_pasta` – pasta de saída (default: `extraidos`)
- `-q` – menos mensagens

## Um PDF por vez

### Extrair e ver na tela

```bash
python extrator_folha_adiantamento.py "Folha adiantamento - 01.26.pdf"
```

### Salvar resultado em JSON

```bash
python extrator_folha_adiantamento.py "Folha adiantamento - 01.26.pdf" --json saida.json
```

### Salvar primeira tabela em CSV

```bash
python extrator_folha_adiantamento.py "Folha Mensal - 01.26.pdf" --csv saida.csv
```

### Modo silencioso (só gera arquivos)

```bash
python extrator_folha_adiantamento.py "Folha adiantamento - 01.26.pdf" --json saida.json -q
```

## O que é extraído

- **Texto completo** de todas as páginas
- **Tabelas** detectadas em cada página
- **Resumo**: período (mês/ano), valores em reais encontrados e informações das tabelas

O script tenta inferir mês/ano a partir do nome ou do conteúdo (ex.: `01.26` → janeiro/2026).

## Arquivos na pasta

- **Folha adiantamento - MM.AA.pdf** – folha de adiantamento
- **Folha Mensal - MM.AA.pdf** – folha mensal (ex.: 01.25 a 12.25, 01.26)

Use `extrair_todos.py` para processar todos de uma vez.

## Dependência

- **pdfplumber** – extração de texto e tabelas de PDF
