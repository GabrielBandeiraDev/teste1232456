#!/usr/bin/env python3
"""
Extrator de dados de PDF - Folha de Adiantamento

Extrai texto e tabelas de PDFs de folha de adiantamento.
Uso:
  python extrator_folha_adiantamento.py <caminho_do.pdf>
  python extrator_folha_adiantamento.py <caminho_do.pdf> --json saida.json
  python extrator_folha_adiantamento.py <caminho_do.pdf> --csv saida.csv
"""

import argparse
import json
import re
import sys
from pathlib import Path


def extrair_com_pdfplumber(pdf_path: str) -> dict:
    """Extrai todo o texto e tabelas do PDF usando pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        print("Erro: instale pdfplumber com: pip install pdfplumber", file=sys.stderr)
        sys.exit(1)

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")

    resultado = {
        "arquivo": path.name,
        "paginas": [],
        "texto_completo": "",
        "tabelas": [],
        "resumo": {},
    }

    with pdfplumber.open(pdf_path) as pdf:
        resultado["total_paginas"] = len(pdf.pages)

        for num, page in enumerate(pdf.pages, 1):
            # Texto da página
            text = page.extract_text()
            if text:
                resultado["texto_completo"] += f"\n--- Página {num} ---\n{text}"
                resultado["paginas"].append({"numero": num, "texto": text})
            else:
                resultado["paginas"].append({"numero": num, "texto": ""})

            # Tabelas da página
            tables = page.extract_tables()
            for t in tables:
                if t and any(cell for row in t for cell in (row or []) if cell):
                    resultado["tabelas"].append({"pagina": num, "dados": t})

    resultado["resumo"] = _extrair_resumo(resultado["texto_completo"], resultado["tabelas"])
    return resultado


def _extrair_resumo(texto: str, tabelas: list) -> dict:
    """Tenta extrair campos comuns de folha de adiantamento (período, totais, etc.)."""
    resumo = {}

    # Período no nome do arquivo (ex: 01.26 = jan/2026)
    match = re.search(r"(\d{2})\.(\d{2})", texto)
    if match:
        mes, ano = match.groups()
        resumo["mes"] = mes
        resumo["ano"] = "20" + ano if int(ano) < 100 else ano

    # Valores em reais (padrão R$ 1.234,56 ou 1.234,56)
    valores = re.findall(r"R?\$?\s*([\d.]{1,10},\d{2})", texto)
    if valores:
        resumo["valores_encontrados"] = [v.strip() for v in valores[:50]]

    # Números que parecem totais (linhas com "total" por perto)
    linhas = texto.lower().split("\n")
    for i, linha in enumerate(linhas):
        if "total" in linha:
            nums = re.findall(r"[\d.]{1,15},\d{2}", linha)
            if nums:
                resumo["total_linha"] = nums

    # Se temos tabelas, tentar primeira linha como cabeçalho e montar lista de registros
    if tabelas:
        resumo["quantidade_tabelas"] = len(tabelas)
        for idx, tb in enumerate(tabelas):
            dados = tb.get("dados", [])
            if len(dados) > 1:
                resumo[f"tabela_{idx + 1}_linhas"] = len(dados)
                resumo[f"tabela_{idx + 1}_colunas"] = len(dados[0]) if dados[0] else 0

    return resumo


def main():
    parser = argparse.ArgumentParser(description="Extrai dados de PDF de Folha de Adiantamento")
    parser.add_argument("pdf", help="Caminho do arquivo PDF")
    parser.add_argument("--json", metavar="ARQUIVO", help="Salvar resultado em JSON")
    parser.add_argument("--csv", metavar="ARQUIVO", help="Salvar tabelas em CSV (primeira tabela)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Não imprimir texto na tela")
    args = parser.parse_args()

    pdf_path = args.pdf
    if not Path(pdf_path).exists():
        print(f"Erro: arquivo não encontrado: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Processando: {pdf_path}", file=sys.stderr)
    dados = extrair_com_pdfplumber(pdf_path)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"JSON salvo em: {args.json}", file=sys.stderr)

    if args.csv and dados["tabelas"]:
        import csv
        tabela = dados["tabelas"][0]["dados"]
        with open(args.csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerows(tabela)
        print(f"CSV salvo em: {args.csv}", file=sys.stderr)

    if not args.quiet:
        print("\n" + "=" * 60)
        print("TEXTO EXTRAÍDO")
        print("=" * 60)
        print(dados["texto_completo"] or "(nenhum texto)")
        print("\n" + "=" * 60)
        print("RESUMO")
        print("=" * 60)
        print(json.dumps(dados["resumo"], ensure_ascii=False, indent=2))
        if dados["tabelas"]:
            print("\n" + "=" * 60)
            print("TABELAS")
            print("=" * 60)
            for i, tb in enumerate(dados["tabelas"]):
                print(f"\n--- Tabela {i + 1} (página {tb['pagina']}) ---")
                for row in tb["dados"]:
                    print(row)

    return dados


if __name__ == "__main__":
    main()
