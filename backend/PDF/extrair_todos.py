#!/usr/bin/env python3
"""
Processa todos os PDFs da pasta e salva os dados extraídos.

Uso:
  python extrair_todos.py              # processa a pasta atual
  python extrair_todos.py --pasta .    # mesmo
  python extrair_todos.py --pasta /caminho/para/pdfs
"""

import argparse
import json
import sys
from pathlib import Path

# Importa o extrator existente
from extrator_folha_adiantamento import extrair_com_pdfplumber


def nome_saida(nome_pdf: str, sufixo: str = "json") -> str:
    """Gera nome de arquivo seguro para saída (sem espaços problemáticos)."""
    base = Path(nome_pdf).stem
    # Substitui espaços e caracteres especiais
    seguro = base.replace(" ", "_").replace(".", "_")
    return f"{seguro}.{sufixo}"


def main():
    parser = argparse.ArgumentParser(description="Extrai dados de todos os PDFs de uma pasta")
    parser.add_argument(
        "--pasta",
        default=".",
        help="Pasta onde estão os PDFs (default: pasta atual)",
    )
    parser.add_argument(
        "--saida",
        default="extraidos",
        help="Pasta onde salvar JSON/CSV (default: extraidos)",
    )
    parser.add_argument("--csv", action="store_true", help="Gerar também arquivo CSV por PDF")
    parser.add_argument("-q", "--quiet", action="store_true", help="Menos mensagens")
    args = parser.parse_args()

    pasta = Path(args.pasta)
    pasta_saida = Path(args.saida)
    if not pasta.is_dir():
        print(f"Erro: pasta não encontrada: {pasta}", file=sys.stderr)
        sys.exit(1)

    pasta_saida.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(pasta.glob("*.pdf"))

    if not pdfs:
        print(f"Nenhum PDF encontrado em: {pasta.absolute()}", file=sys.stderr)
        sys.exit(0)

    if not args.quiet:
        print(f"Encontrados {len(pdfs)} PDF(s). Saída em: {pasta_saida.absolute()}\n")

    erros = []
    for i, path_pdf in enumerate(pdfs, 1):
        nome = path_pdf.name
        if not args.quiet:
            print(f"[{i}/{len(pdfs)}] {nome} ...", end=" ", flush=True)
        try:
            dados = extrair_com_pdfplumber(str(path_pdf))

            # JSON
            arq_json = pasta_saida / nome_saida(nome, "json")
            with open(arq_json, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            if not args.quiet:
                print(f"JSON ok", end="")

            # CSV (primeira tabela)
            if args.csv and dados.get("tabelas"):
                import csv
                arq_csv = pasta_saida / nome_saida(nome, "csv")
                with open(arq_csv, "w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f, delimiter=";")
                    w.writerows(dados["tabelas"][0]["dados"])
                if not args.quiet:
                    print(f", CSV ok", end="")

            if not args.quiet:
                print()

        except Exception as e:
            erros.append((nome, str(e)))
            if not args.quiet:
                print(f"ERRO: {e}")

    if erros:
        print(f"\n{len(erros)} arquivo(s) com erro:", file=sys.stderr)
        for nome, msg in erros:
            print(f"  - {nome}: {msg}", file=sys.stderr)
    elif not args.quiet:
        print(f"\nConcluído. {len(pdfs)} arquivo(s) processado(s).")


if __name__ == "__main__":
    main()
