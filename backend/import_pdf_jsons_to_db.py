#!/usr/bin/env python3
"""
Zera dados de jornada (absenteísmo e base_kpi) e importa os JSONs extraídos
da pasta backend/PDF/extraidos, vinculando cada registro ao colaborador (nome, matrícula).
Extrai também horas extras e faltas dos PDFs.

Uso (a partir da raiz do projeto ou do backend):
  python backend/import_pdf_jsons_to_db.py
  python import_pdf_jsons_to_db.py --pasta /caminho/para/backend/PDF/extraidos
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Encontrar backend e banco
SCRIPT_DIR = Path(__file__).parent.resolve()
if (SCRIPT_DIR / "database.db").exists():
    DB_FILE = SCRIPT_DIR / "database.db"
else:
    DB_FILE = SCRIPT_DIR.parent / "backend" / "database.db"

# Atualizar caminho para PDF dentro do backend
DEFAULT_EXTRAIDOS = SCRIPT_DIR / "PDF" / "extraidos"
if not DEFAULT_EXTRAIDOS.exists():
    DEFAULT_EXTRAIDOS = SCRIPT_DIR.parent / "PDF" / "extraidos"

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _parse_valor(s):
    if not s:
        return 0.0
    s = str(s).replace(".", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _extrair_periodo(texto):
    """Extrai mês e ano do texto (ex: Mês/Ano: 01/2026)."""
    m = re.search(r"Mês/Ano:\s*(\d{2})/(\d{4})", texto, re.IGNORECASE)
    if m:
        mes_num = int(m.group(1))
        ano = int(m.group(2))
        mes_nome = MESES[mes_num - 1] if 1 <= mes_num <= 12 else "Janeiro"
        return mes_nome, ano
    m = re.search(r"(\d{2})\.(\d{2})", texto)
    if m:
        mes_num = int(m.group(1))
        ano = int(m.group(2))
        ano = 2000 + ano if ano < 100 else ano
        mes_nome = MESES[mes_num - 1] if 1 <= mes_num <= 12 else "Janeiro"
        return mes_nome, ano
    return "Janeiro", 2025


def _extrair_colaboradores(texto):
    """Extrai lista de colaboradores do texto (blocos Funcionário: N - NOME Adm: ...)."""
    resultado = []
    # Split por "Funcionário: NNN - " mantendo o número e o resto do bloco
    partes = re.split(r"Funcionário:\s*(\d+)\s*-\s*", texto)
    for i in range(1, len(partes), 2):
        if i + 1 >= len(partes):
            break
        matricula = (partes[i] or "").strip()
        bloco = partes[i + 1] or ""
        if not matricula.isdigit():
            continue
        # Nome até "Adm:" ou fim da linha
        nome_match = re.search(r"^([^\n]+?)(?:\s+Adm:|\n)", bloco, re.MULTILINE)
        nome = nome_match.group(1).strip() if nome_match else ""
        if not nome:
            continue
        # Adm e Função
        adm_match = re.search(r"Adm:\s*(\d{2}/\d{2}/\d{4})", bloco)
        funcao_match = re.search(r"Função:\s*([^\n]+)", bloco)
        adm = adm_match.group(1) if adm_match else ""
        funcao = funcao_match.group(1).strip() if funcao_match else ""
        # Salário Base
        sal_match = re.search(r"Salário Base:\s*([\d.,]+)", bloco)
        salario = _parse_valor(sal_match.group(1)) if sal_match else 0.0
        # Líquido a Receber
        liq_match = re.search(r"Líquido a Receber:\s*([\d.,]+)", bloco)
        liquido = _parse_valor(liq_match.group(1)) if liq_match else 0.0
        # Total de Vencimentos (folha mensal)
        venc_match = re.search(r"Total de Vencimentos:\s*([\d.,]+)", bloco)
        vencimentos = _parse_valor(venc_match.group(1)) if venc_match else liquido or salario
        
        # Extrair Horas Extras (padrões: "00013 HORA EXTRA 100% 08:03" ou "00009 HORA EXTRA 050% 08:00" ou "00220 HORA EXTRA 55% 01:00")
        horas_extras = 0.0
        horas_extra_matches = re.findall(r"HORA EXTRA\s+\d+%\s+(\d{1,2}):(\d{2})", bloco, re.IGNORECASE)
        for horas_str, minutos_str in horas_extra_matches:
            try:
                horas = int(horas_str)
                minutos = int(minutos_str)
                horas_extras += horas + (minutos / 60.0)
            except (ValueError, IndexError):
                continue
        
        # Extrair Faltas (padrão: "00206 FALTAS INJUSTIFICADAS 3")
        faltas = 0.0
        faltas_match = re.search(r"FALTAS INJUSTIFICADAS\s+(\d+)", bloco, re.IGNORECASE)
        if faltas_match:
            try:
                faltas = float(faltas_match.group(1))
            except (ValueError, IndexError):
                pass
        
        # Calcular valor da hora extra baseado no salário
        horas_mes = 220  # 44h semanais * 5 semanas
        valor_hora_normal = salario / horas_mes if horas_mes > 0 and salario > 0 else 0
        valor_hora_extra = valor_hora_normal * 1.5  # 50% adicional (1.5x)
        custo_horas_extras = horas_extras * valor_hora_extra
        
        resultado.append({
            "matricula": matricula,
            "nome": nome,
            "adm": adm,
            "funcao": funcao,
            "salario": salario,
            "liquido": liquido,
            "vencimentos": vencimentos,
            "horas_extras": round(horas_extras, 2),
            "faltas": faltas,
            "custo_horas_extras": round(custo_horas_extras, 2),
            "valor_hora_extra": round(valor_hora_extra, 2),
        })
    return resultado


def _extrair_totais_folha_mensal(texto):
    """Extrai totais da folha mensal (Total de Vencimentos, Descontos, Líquido, FGTS, etc.)."""
    totais = {}
    # Padrões no final do documento (totalizadores)
    patterns = [
        (r"Total de Vencimentos\s+[\d.,]+\s+Total de Descontos\s+([\d.,]+)\s+Total Líquido\s+([\d.,]+)", "descontos", "liquido"),
        (r"TOTAL DE VENCIMENTOS\s+([\d.,]+)", "total_vencimentos", None),
        (r"Total de Vencimentos\s+([\d.,]+)", "total_vencimentos", None),
        (r"Total de Descontos\s+([\d.,]+)", "total_descontos", None),
        (r"Total Líquido\s+([\d.,]+)", "total_liquido", None),
        (r"TOTAL LíQUIDO\s+([\d.,]+)", "total_liquido", None),
        (r"VALOR DO FGTS\s+([\d.,]+)", "fgts", None),
    ]
    for pattern, key1, key2 in patterns:
        m = re.search(pattern, texto, re.IGNORECASE)
        if m:
            if key2:
                totais[key1] = _parse_valor(m.group(1))
                totais[key2] = _parse_valor(m.group(2))
            else:
                totais[key1] = _parse_valor(m.group(1))
    # Também procurar linha "Total de Vencimentos X Total de Descontos Y Total Líquido Z"
    m = re.search(
        r"Total de Vencimentos\s+([\d.,]+)\s+Total de Descontos\s+([\d.,]+)\s+Total Líquido\s+([\d.,]+)",
        texto, re.IGNORECASE
    )
    if m:
        totais["total_vencimentos"] = _parse_valor(m.group(1))
        totais["total_descontos"] = _parse_valor(m.group(2))
        totais["total_liquido"] = _parse_valor(m.group(3))
    return totais


def carregar_json_e_extrair(caminho_json):
    """Carrega um JSON da pasta extraidos e retorna (periodo, colaboradores, totais)."""
    with open(caminho_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    texto = data.get("texto_completo", "") or "".join(
        p.get("texto", "") for p in data.get("paginas", [])
    )
    mes_nome, ano = _extrair_periodo(texto)
    colaboradores = _extrair_colaboradores(texto)
    totais = {}
    # Folha Mensal tem totalizadores no final
    if "Folha Mensal" in data.get("arquivo", "") or "Mensal" in str(caminho_json):
        totais = _extrair_totais_folha_mensal(texto)
        if not totais and colaboradores:
            total_venc = sum(c.get("vencimentos") or c.get("liquido") or c.get("salario", 0) for c in colaboradores)
            total_liq = sum(c.get("liquido", 0) for c in colaboradores)
            totais = {"total_vencimentos": total_venc, "total_liquido": total_liq}
    return mes_nome, ano, colaboradores, totais


def run(pasta_extraidos, zerar_jornada=True, dry_run=False):
    import sqlite3

    pasta = Path(pasta_extraidos).resolve()
    if not pasta.is_dir():
        print(f"Erro: pasta não encontrada: {pasta}", flush=True)
        return 1

    jsons = sorted(pasta.glob("*.json"))
    print(f"Pasta: {pasta} | JSONs: {len(jsons)}", flush=True)
    if not jsons:
        print(f"Nenhum JSON em: {pasta}", flush=True)
        return 0

    # Coletar todos os registros de absenteísmo e base_kpi
    registros_abs = []  # (cpf, nome, matricula, mes, ano, salario, horas_extras, custo_he, faltas, abonos, valor_hora_extra)
    registros_kpi = []  # (kpi, mes, ano, valor, tipo)

    for path_json in jsons:
        try:
            mes_nome, ano, colaboradores, totais = carregar_json_e_extrair(path_json)
        except Exception as e:
            print(f"Erro ao processar {path_json.name}: {e}")
            continue
        for c in colaboradores:
            registros_abs.append({
                "cpf": "",  # PDF não traz CPF; vínculo por Nome no frontend
                "nome": c["nome"],
                "matricula": c["matricula"],
                "mes": mes_nome,
                "ano": ano,
                "salario": c.get("salario") or c.get("vencimentos") or 0,
                "horas_extras": c.get("horas_extras", 0),
                "custo_horas_extras": c.get("custo_horas_extras", 0),
                "faltas": c.get("faltas", 0),
                "abonos": 0,  # Não extraído ainda dos PDFs
                "valor_hora_extra": c.get("valor_hora_extra", 0),
            })
        if totais:
            v = totais.get("total_vencimentos", 0)
            if v > 0:
                registros_kpi.append(("Folha de pagamento", mes_nome, ano, v, "Folha"))
            v = totais.get("total_descontos", 0)
            if v > 0:
                registros_kpi.append(("Descontos Total", mes_nome, ano, v, "Folha"))
            v = totais.get("total_liquido", 0)
            if v > 0:
                registros_kpi.append(("Líquido Total", mes_nome, ano, v, "Folha"))
            v = totais.get("fgts", 0)
            if v > 0:
                registros_kpi.append(("Encargos FGTS", mes_nome, ano, v, "Folha"))

    if dry_run:
        print(f"Dry-run: {len(registros_abs)} registros de absenteísmo, {len(registros_kpi)} de base_kpi", flush=True)
        for r in registros_abs[:5]:
            print("  ", r, flush=True)
        return 0

    if not DB_FILE.exists():
        print(f"Erro: banco não encontrado: {DB_FILE}")
        return 1

    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()

    # Adicionar coluna Matricula se não existir
    try:
        cursor.execute("ALTER TABLE absenteísmo ADD COLUMN Matricula TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    if zerar_jornada:
        cursor.execute("DELETE FROM absenteísmo")
        cursor.execute("DELETE FROM base_kpi")
        conn.commit()
        print("Tabelas absenteísmo e base_kpi zeradas.")

    # Inserir absenteísmo (com Matricula se a coluna existir)
    cursor.execute("PRAGMA table_info(absenteísmo)")
    col_names = [r[1] for r in cursor.fetchall()]
    tem_matricula = "Matricula" in col_names

    for r in registros_abs:
        if tem_matricula:
            cursor.execute(
                """INSERT INTO absenteísmo (CPF, Nome, Matricula, Mês, Ano, Horas_Extras, Custo_Horas_Extras, Faltas, Abonos, Salário, Valor_Hora_Extra)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["cpf"], r["nome"], r["matricula"], r["mes"], r["ano"],
                    r["horas_extras"], r["custo_horas_extras"], r["faltas"], r["abonos"],
                    r["salario"], r["valor_hora_extra"],
                ),
            )
        else:
            cursor.execute(
                """INSERT INTO absenteísmo (CPF, Nome, Mês, Ano, Horas_Extras, Custo_Horas_Extras, Faltas, Abonos, Salário, Valor_Hora_Extra)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["cpf"], r["nome"], r["mes"], r["ano"],
                    r["horas_extras"], r["custo_horas_extras"], r["faltas"], r["abonos"],
                    r["salario"], r["valor_hora_extra"],
                ),
            )

    for r in registros_kpi:
        cursor.execute(
            "INSERT INTO base_kpi (KPI, Mês, Ano, Valor, Tipo) VALUES (?, ?, ?, ?, ?)",
            (r[0], r[1], r[2], r[3], r[4]),
        )

    conn.commit()
    conn.close()
    print(f"Importados: {len(registros_abs)} registros em absenteísmo, {len(registros_kpi)} em base_kpi.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Importa JSONs da pasta backend/PDF/extraidos para o banco (jornada e folha)")
    parser.add_argument("--pasta", default=str(DEFAULT_EXTRAIDOS.resolve()), help="Pasta com os JSONs (extraidos)")
    parser.add_argument("--no-zerar", action="store_true", help="Não zerar absenteísmo e base_kpi antes de importar")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostrar o que seria importado")
    args = parser.parse_args()
    return run(args.pasta, zerar_jornada=not args.no_zerar, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
