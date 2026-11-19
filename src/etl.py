"""
ETL da Tabela 913 (Data.Rio / INEP): cursos de graduação presenciais
no Brasil e nas 12 maiores capitais, 2000-2022.

Pipeline determinístico: bruto (.xls, uma aba por ano) -> formato longo
(tidy) -> validações -> métricas derivadas -> persistência (csv.gz + JSON).

Uso:
    python -m src.etl                       # usa data/raw/913.xls
    python -m src.etl --input outro.xlsx    # .xls (xlrd) ou .xlsx (openpyxl)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

LOG = logging.getLogger("etl")

ROOT = Path(__file__).resolve().parents[1]
RAW_DEFAULT = ROOT / "data" / "raw" / "913.xls"
PROCESSED = ROOT / "data" / "processed"

BRASIL = "Brasil"
AGREGADO = "12 Capitais"


# --------------------------------------------------------------------------
# Utilidades de parsing
# --------------------------------------------------------------------------
def parse_inteiro(valor) -> float:
    """Converte '35 765', '35\u00a0765' ou 10585 em número inteiro (NaN se vazio).

    Em 2022 o separador de milhar veio como espaço (texto), não como número.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return np.nan
    if isinstance(valor, (int, np.integer)):
        return float(valor)
    if isinstance(valor, float):
        return float(round(valor))
    digitos = re.sub(r"\D", "", str(valor))
    return float(digitos) if digitos else np.nan


def parse_percentual(valor) -> float:
    """Converte percentual numérico ou textual ('2,2' / '2.2') em float."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return np.nan
    if isinstance(valor, (int, float, np.integer, np.floating)):
        return float(valor)
    txt = str(valor).strip().replace("%", "").replace("\u00a0", "").replace(" ", "")
    try:
        return float(txt.replace(",", "."))
    except ValueError:
        return np.nan


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Extração
# --------------------------------------------------------------------------
def extrair_aba(bruto: pd.DataFrame, ano: int) -> tuple[pd.DataFrame, dict]:
    """Extrai uma aba (layout com cabeçalhos/rodapés) para formato tidy.

    As linhas são localizadas pelo conteúdo ('Capitais' = cabeçalho,
    'Fonte' = rodapé) e não por índice fixo. A ordem das capitais muda a
    cada ano (ranking), portanto a chave de junção é o nome, nunca a posição.
    """
    col0 = bruto.iloc[:, 0].astype(str).str.strip()

    idx_cab = col0[col0.eq("Capitais")].index
    if len(idx_cab) != 1:
        raise ValueError(f"[{ano}] cabeçalho 'Capitais' não encontrado de forma única")

    corpo = bruto.iloc[idx_cab[0] + 1:, :3].copy()
    corpo.columns = ["localidade", "total_raw", "pct_raw"]
    corpo = corpo.dropna(subset=["localidade"])
    corpo["localidade"] = corpo["localidade"].astype(str).str.strip()
    corpo = corpo[~corpo["localidade"].str.startswith("Fonte")].copy()

    titulo = next((str(v) for v in bruto.iloc[:6, 0] if str(v).startswith("Tabela")), "")
    rodape = next((str(v).strip() for v in bruto.iloc[:, 0] if str(v).startswith("Fonte")), "")

    corpo["ano"] = ano
    corpo["total_cursos"] = corpo["total_raw"].map(parse_inteiro)
    corpo["pct_oficial"] = corpo["pct_raw"].map(parse_percentual)
    corpo["tipo_texto_original"] = corpo["total_raw"].map(lambda v: type(v).__name__)
    corpo["tipo"] = np.where(
        corpo["localidade"].eq(BRASIL), "nacional",
        np.where(corpo["localidade"].eq(AGREGADO), "agregado", "capital"),
    )
    meta = {
        "ano": ano,
        "titulo": re.sub(r"\s+", " ", titulo),
        "fonte": re.sub(r"\s+", " ", rodape),
    }
    return corpo.drop(columns=["total_raw", "pct_raw"]), meta


def carregar_planilha(caminho: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Lê todas as abas anuais. Retorna (long, proveniência, abas_descartadas)."""
    engine = "xlrd" if caminho.suffix.lower() == ".xls" else "openpyxl"
    xl = pd.ExcelFile(caminho, engine=engine)

    partes, metas, descartadas = [], [], []
    for aba in xl.sheet_names:
        if not re.fullmatch(r"\d{4}", aba):
            descartadas.append(aba)  # rastreabilidade: nada é descartado em silêncio
            LOG.warning("Aba descartada (não anual): %s", aba)
            continue
        df, meta = extrair_aba(xl.parse(aba, header=None), int(aba))
        partes.append(df)
        metas.append(meta)

    longo = pd.concat(partes, ignore_index=True)
    longo["total_cursos"] = longo["total_cursos"].astype("Int64")
    longo = longo.sort_values(["ano", "tipo", "localidade"]).reset_index(drop=True)
    return longo, pd.DataFrame(metas), descartadas


# --------------------------------------------------------------------------
# Validação
# --------------------------------------------------------------------------
def validar(longo: pd.DataFrame) -> dict:
    """Checks de qualidade. Retorna relatório (não altera os dados)."""
    rel: dict = {}
    rel["n_linhas"] = int(len(longo))
    rel["anos"] = [int(longo["ano"].min()), int(longo["ano"].max())]
    rel["n_anos"] = int(longo["ano"].nunique())
    rel["nulos_total_cursos"] = int(longo["total_cursos"].isna().sum())
    rel["capitais_distintas"] = sorted(longo.loc[longo.tipo == "capital", "localidade"].unique())
    rel["duplicatas_ano_localidade"] = int(longo.duplicated(["ano", "localidade"]).sum())
    rel["abas_com_valor_textual"] = sorted(
        longo.loc[longo.tipo_texto_original.eq("str"), "ano"].unique().astype(int).tolist()
    )

    soma = longo[longo.tipo == "capital"].groupby("ano")["total_cursos"].sum()
    agreg = longo[longo.tipo == "agregado"].set_index("ano")["total_cursos"]
    rel["anos_onde_soma_capitais_difere_do_agregado"] = [int(a) for a in soma.index if soma[a] != agreg[a]]

    br = longo[longo.tipo == "nacional"].set_index("ano")["total_cursos"]
    pct_calc = longo["total_cursos"].astype(float) / longo["ano"].map(br).astype(float) * 100
    erro = (pct_calc - longo["pct_oficial"]).abs()
    rel["erro_max_pct_vs_recalculado_pp"] = round(float(erro.max()), 4)
    rel["anos_com_erro_pct_maior_que_0_05pp"] = sorted(
        int(a) for a, v in erro.groupby(longo["ano"]).max().items() if v > 0.05
    )
    return rel


# --------------------------------------------------------------------------
# Métricas derivadas
# --------------------------------------------------------------------------
def construir_metricas(longo: pd.DataFrame) -> pd.DataFrame:
    """Métricas por ano x localidade (capitais + agregado + Brasil)."""
    df = longo[["ano", "localidade", "tipo", "total_cursos", "pct_oficial"]].copy()
    df["total_cursos"] = df["total_cursos"].astype(float)

    br = df[df.tipo == "nacional"].set_index("ano")["total_cursos"]
    ag = df[df.tipo == "agregado"].set_index("ano")["total_cursos"]

    df["pct_brasil_calc"] = df["total_cursos"] / df["ano"].map(br) * 100
    df["pct_nas_12_capitais"] = np.where(
        df.tipo == "capital", df["total_cursos"] / df["ano"].map(ag) * 100, np.nan
    )

    df = df.sort_values(["localidade", "ano"])
    g = df.groupby("localidade")["total_cursos"]
    df["var_abs_anual"] = g.diff()
    df["var_pct_anual"] = g.pct_change() * 100
    df["indice_base_2000"] = df["total_cursos"] / g.transform("first") * 100

    cap = df.tipo == "capital"
    df["ranking"] = np.nan
    df.loc[cap, "ranking"] = df[cap].groupby("ano")["total_cursos"].rank(method="min", ascending=False)
    df["ranking"] = df["ranking"].astype("Int64")
    return df.sort_values(["ano", "tipo", "total_cursos"], ascending=[True, True, False]).reset_index(drop=True)


def resumo_por_localidade(metricas: pd.DataFrame) -> pd.DataFrame:
    """CAGR, variação total, pico e ranking inicial/final por localidade."""
    a0, a1 = int(metricas.ano.min()), int(metricas.ano.max())
    n = a1 - a0
    linhas = []
    for loc, g in metricas.groupby("localidade"):
        g = g.sort_values("ano")
        ini, fim = g.iloc[0], g.iloc[-1]
        pico = g.loc[g.total_cursos.idxmax()]
        linhas.append({
            "localidade": loc,
            "tipo": ini["tipo"],
            f"cursos_{a0}": int(ini.total_cursos),
            f"cursos_{a1}": int(fim.total_cursos),
            "var_abs": int(fim.total_cursos - ini.total_cursos),
            "var_pct_total": (fim.total_cursos / ini.total_cursos - 1) * 100,
            "cagr_pct": ((fim.total_cursos / ini.total_cursos) ** (1 / n) - 1) * 100,
            "ano_pico": int(pico.ano),
            "cursos_pico": int(pico.total_cursos),
            "var_pct_desde_pico": (fim.total_cursos / pico.total_cursos - 1) * 100,
            f"rank_{a0}": ini["ranking"],
            f"rank_{a1}": fim["ranking"],
            f"pct_brasil_{a0}": ini.pct_brasil_calc,
            f"pct_brasil_{a1}": fim.pct_brasil_calc,
        })
    return pd.DataFrame(linhas).sort_values("cagr_pct", ascending=False).reset_index(drop=True)


def indicadores_concentracao(metricas: pd.DataFrame) -> pd.DataFrame:
    """Dispersão e concentração entre as 12 capitais, por ano."""
    cap = metricas[metricas.tipo == "capital"]

    def hhi(s: pd.Series) -> float:  # Herfindahl-Hirschman (0-10000)
        p = s / s.sum() * 100
        return float((p ** 2).sum())

    def gini(s: pd.Series) -> float:
        x = np.sort(s.to_numpy(dtype=float))
        n = len(x)
        return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))

    g = cap.groupby("ano")["total_cursos"]
    out = pd.DataFrame({
        "media": g.mean(), "mediana": g.median(), "desvio_padrao": g.std(),
        "cv": g.std() / g.mean(), "hhi": g.apply(hhi), "gini": g.apply(gini),
        "pct_top1_nas_12": g.max() / g.sum() * 100,
    })
    out["pct_12_capitais_no_brasil"] = (
        metricas[metricas.tipo == "agregado"].set_index("ano")["pct_brasil_calc"]
    )
    return out.reset_index()


def sinalizar_outliers(metricas: pd.DataFrame, limite: float = 3.5) -> pd.DataFrame:
    """Variações anuais atípicas por z-score robusto (mediana/MAD) em cada série."""
    dados = metricas.dropna(subset=["var_pct_anual"]).copy()

    def zrobusto(s: pd.Series) -> pd.Series:
        mad = (s - s.median()).abs().median()
        return 0.6745 * (s - s.median()) / mad if mad else s * 0

    dados["z_robusto"] = dados.groupby("localidade")["var_pct_anual"].transform(zrobusto)
    cols = ["ano", "localidade", "total_cursos", "var_abs_anual", "var_pct_anual", "z_robusto"]
    return (dados.loc[dados.z_robusto.abs() >= limite, cols]
            .sort_values("z_robusto", key=np.abs, ascending=False).reset_index(drop=True))


# --------------------------------------------------------------------------
# Persistência
# --------------------------------------------------------------------------
def executar(entrada: Path = RAW_DEFAULT, saida: Path = PROCESSED) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    longo, prov, descartadas = carregar_planilha(entrada)

    rel = validar(longo)
    rel["abas_descartadas"] = descartadas
    rel["arquivo_bruto"] = {"nome": entrada.name, "sha256": sha256(entrada)}

    metricas = construir_metricas(longo)
    kw = dict(index=False, float_format="%.6f")

    longo.drop(columns=["tipo_texto_original"]).to_csv(
        saida / "cursos_graduacao_long.csv.gz", compression="gzip", **kw)
    metricas.to_csv(saida / "metricas_capitais.csv.gz", compression="gzip", **kw)
    resumo_por_localidade(metricas).to_csv(saida / "resumo_por_localidade.csv", **kw)
    indicadores_concentracao(metricas).to_csv(saida / "indicadores_concentracao.csv", **kw)
    sinalizar_outliers(metricas).to_csv(saida / "outliers_variacao_anual.csv", **kw)
    prov.to_csv(saida / "proveniencia_abas.csv", index=False)
    (saida / "qa_report.json").write_text(
        json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
    LOG.info("Processamento concluído: %d linhas em %s", len(longo), saida)
    return rel


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=RAW_DEFAULT)
    ap.add_argument("--output", type=Path, default=PROCESSED)
    args = ap.parse_args()
    print(json.dumps(executar(args.input, args.output), ensure_ascii=False, indent=2))
