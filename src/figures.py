"""
Gera as figuras estáticas (PNG, 200 dpi) e o arquivo docs/assets/data.js
(dados processados em JSON) consumido pelos gráficos interativos Plotly.js
do artigo. Depende apenas de data/processed/ (saída do src.etl).

Uso:  python -m src.figures
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
ASSETS = ROOT / "docs" / "assets"

# Paleta categórica (Okabe-Ito estendida) - distinguível em daltonismo
CORES = {
    "São Paulo": "#0072B2", "Rio de Janeiro": "#D55E00", "Brasília": "#009E73",
    "Belo Horizonte": "#CC79A7", "Salvador": "#E69F00", "Curitiba": "#56B4E9",
    "Recife": "#7B3294", "Fortaleza": "#B2182B", "Manaus": "#4D9221",
    "Porto Alegre": "#999999", "Goiânia": "#8C510A", "Belém": "#1B7837",
}
COR_BR, COR_12 = "#222222", "#0072B2"

plt.rcParams.update({
    "figure.dpi": 100, "savefig.dpi": 200, "font.size": 10.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "axes.titleweight": "bold",
    "axes.titlesize": 11.5, "legend.frameon": False,
})


def milhar(x, _=None):
    return f"{x:,.0f}".replace(",", ".")


def carregar():
    m = pd.read_csv(PROC / "metricas_capitais.csv.gz")
    return (m, pd.read_csv(PROC / "resumo_por_localidade.csv"),
            pd.read_csv(PROC / "indicadores_concentracao.csv"))


def salvar(fig, nome):
    fig.savefig(ASSETS / nome, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ figuras
def fig1_evolucao(m):
    br = m[m.localidade == "Brasil"].set_index("ano")
    cp = m[m.localidade == "12 Capitais"].set_index("ano")
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.15, 1]})
    a.plot(br.index, br.total_cursos, color=COR_BR, lw=2.4, label="Brasil")
    a.plot(cp.index, cp.total_cursos, color=COR_12, lw=2.4, label="12 maiores capitais")
    a.yaxis.set_major_formatter(milhar)
    a.set_title("(a) Cursos de graduação presenciais")
    a.set_ylabel("Número de cursos"); a.legend(loc="upper left")
    a.set_ylim(0, 40000)
    a.scatter([2019], [br.total_cursos[2019]], color=COR_BR, zorder=3, s=22)
    a.annotate("Pico nacional: 35.898 (2019)", (2019, br.total_cursos[2019]), (2009.2, 37800),
               arrowprops=dict(arrowstyle="-", color="#777"), fontsize=9, color="#444")

    cores = np.where(br.var_pct_anual >= 0, COR_BR, "#D55E00")
    b.bar(br.index[1:], br.var_pct_anual[1:], color=cores[1:], width=0.75, label="Brasil")
    b.plot(cp.index[1:], cp.var_pct_anual[1:], color=COR_12, lw=2, marker="o", ms=3.5, label="12 capitais")
    b.axhline(0, color="#444", lw=0.8)
    b.set_title("(b) Variação anual (%)"); b.set_ylabel("% em relação ao ano anterior")
    b.annotate("2009: +20,7%\nnas capitais", (2009, 20.6), (2011.2, 18.5), fontsize=9,
               arrowprops=dict(arrowstyle="-", color="#777"))
    b.legend(loc="upper right", bbox_to_anchor=(1, 0.78))
    fig.suptitle("Figura 1 - Expansão e desaceleração da oferta de cursos (2000-2022)", y=1.02, fontweight="bold")
    fig.text(0.01, -0.03, "Fonte: INEP via Data.Rio, Tabela 913. Elaboração própria.", fontsize=8.5, color="#555")
    salvar(fig, "fig1_evolucao.png")


def fig2_participacao(m):
    cp = m[m.localidade == "12 Capitais"].set_index("ano")
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.plot(cp.index, cp.pct_brasil_calc, color=COR_12, lw=2.5, marker="o", ms=4)
    ax.fill_between(cp.index, 25, cp.pct_brasil_calc, color=COR_12, alpha=0.08)
    ax.set_ylim(25, 30.5); ax.set_ylabel("% do total nacional de cursos")
    ax.axvline(2009, color="#D55E00", ls="--", lw=1)
    ax.text(2009.15, 25.25, "salto em 2009\n(+2,0 p.p. em um ano)", color="#D55E00", fontsize=9)
    for ano in (2000, 2004, 2009, 2022):
        ax.annotate(f"{cp.pct_brasil_calc[ano]:.1f}%".replace(".", ","), (ano, cp.pct_brasil_calc[ano]),
                    textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9)
    ax.set_title("Figura 2 - Participação das 12 capitais no total nacional de cursos")
    fig.text(0.01, -0.03, "Fonte: INEP via Data.Rio, Tabela 913. Percentual recalculado (total / Brasil).",
             fontsize=8.5, color="#555")
    salvar(fig, "fig2_participacao.png")


def fig3_cagr(res):
    d = res[res.tipo == "capital"].sort_values("cagr_pct")
    br = res.loc[res.localidade == "Brasil", "cagr_pct"].iloc[0]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ax.barh(d.localidade, d.cagr_pct, color=[CORES[x] for x in d.localidade])
    ax.axvline(br, color="#222", ls="--", lw=1.2)
    ax.text(br + 0.05, -0.75, f"Brasil: {br:.2f}% a.a.".replace(".", ","), fontsize=9)
    for y, (v, a, b) in enumerate(zip(d.cagr_pct, d.cursos_2000, d.cursos_2022)):
        ax.text(v + 0.06, y, f"{v:.1f}% ({milhar(a)}→{milhar(b)})".replace(".", ","), va="center", fontsize=8.8)
    ax.set_xlim(0, 10.3); ax.grid(axis="y", alpha=0)
    ax.set_xlabel("Taxa composta de crescimento anual (CAGR, % a.a.), 2000-2022")
    ax.set_title("Figura 3 - Ritmo de expansão por capital")
    fig.text(0.01, -0.03, "Fonte: INEP via Data.Rio, Tabela 913. Elaboração própria.", fontsize=8.5, color="#555")
    salvar(fig, "fig3_cagr.png")


def fig4_ranking(m):
    d = m[m.tipo == "capital"]
    fig, ax = plt.subplots(figsize=(9.6, 5))
    for loc, g in d.groupby("localidade"):
        g = g.sort_values("ano")
        mudou = g.ranking.iloc[0] != g.ranking.iloc[-1]
        ax.plot(g.ano, g.ranking, color=CORES[loc], lw=2.6 if mudou else 1.4, alpha=1 if mudou else 0.55,
                marker="o", ms=3)
        ax.text(2022.35, g.ranking.iloc[-1], loc, va="center", fontsize=9, color=CORES[loc])
        ax.text(1999.65, g.ranking.iloc[0], loc, va="center", ha="right", fontsize=9, color=CORES[loc])
    ax.invert_yaxis(); ax.set_yticks(range(1, 13)); ax.set_xlim(1995.5, 2026)
    ax.set_xticks(range(2000, 2023, 2)); ax.grid(axis="x", alpha=0.15); ax.grid(axis="y", alpha=0)
    ax.set_ylabel("Posição (1 = mais cursos)")
    ax.set_title("Figura 4 - Ranking das capitais por número de cursos (linhas grossas = posição mudou entre 2000 e 2022)")
    fig.text(0.01, -0.03, "Fonte: INEP via Data.Rio, Tabela 913. Empates recebem a menor posição.", fontsize=8.5, color="#555")
    salvar(fig, "fig4_ranking.png")


def fig5_concentracao(conc):
    fig, (a, b) = plt.subplots(1, 2, figsize=(10.5, 4))
    a.plot(conc.ano, conc.gini, color="#0072B2", lw=2.4)
    a.set_title("(a) Índice de Gini entre as 12 capitais"); a.set_ylim(0.28, 0.42)
    a.annotate(f"{conc.gini.iloc[0]:.3f}".replace(".", ","), (2000, conc.gini.iloc[0]), xytext=(0, 8), textcoords="offset points", ha="center")
    a.annotate(f"{conc.gini.iloc[-1]:.3f}".replace(".", ","), (2022, conc.gini.iloc[-1]), xytext=(0, 8), textcoords="offset points", ha="center")
    b.plot(conc.ano, conc.pct_top1_nas_12, color="#D55E00", lw=2.4)
    b.set_title("(b) Participação de São Paulo nos cursos das 12 capitais (%)")
    b.set_ylim(24, 34)
    b.annotate("pico 2005:\n32,2%", (2005, conc.pct_top1_nas_12[5]), xytext=(2007, 33), fontsize=9,
               arrowprops=dict(arrowstyle="-", color="#777"))
    fig.suptitle("Figura 5 - Desconcentração entre as capitais", y=1.03, fontweight="bold")
    fig.text(0.01, -0.03, "Fonte: INEP via Data.Rio, Tabela 913. Gini calculado sobre os 12 valores anuais.", fontsize=8.5, color="#555")
    salvar(fig, "fig5_concentracao.png")


def fig6_heatmap(m):
    d = m[m.tipo == "capital"].pivot(index="localidade", columns="ano", values="var_pct_anual")
    ordem = (m[(m.tipo == "capital") & (m.ano == 2022)].sort_values("total_cursos", ascending=False).localidade)
    d = d.loc[ordem].iloc[:, :]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    im = ax.imshow(d.values, aspect="auto", cmap="RdBu", vmin=-30, vmax=30)
    ax.set_xticks(range(len(d.columns))); ax.set_xticklabels(d.columns.astype(int), rotation=90, fontsize=8.5)
    ax.set_yticks(range(len(d.index))); ax.set_yticklabels(d.index); ax.grid(False)
    for i in range(d.shape[0]):
        for j in range(d.shape[1]):
            v = d.values[i, j]
            if not np.isnan(v) and abs(v) >= 20:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white" if abs(v) > 25 else "#222")
    cb = fig.colorbar(im, ax=ax, pad=0.01); cb.set_label("Variação anual (%)")
    ax.set_title("Figura 6 - Variação anual do número de cursos por capital (valores ≥ 20% em módulo anotados)")
    fig.text(0.01, -0.03, "Fonte: INEP via Data.Rio, Tabela 913. Escala truncada em ±30% para preservar contraste.", fontsize=8.5, color="#555")
    salvar(fig, "fig6_heatmap.png")


# ------------------------------------------------------------------- dados JS
def exportar_data_js(m, res, conc):
    anos = sorted(m.ano.unique().tolist())
    def serie(loc, col):
        s = m[m.localidade == loc].set_index("ano")[col]
        return [None if pd.isna(s[a]) else round(float(s[a]), 3) for a in anos]
    caps = res[res.tipo == "capital"].localidade.tolist()
    dados = {
        "anos": anos, "cores": CORES, "capitais": caps,
        "cursos": {l: serie(l, "total_cursos") for l in caps + ["Brasil", "12 Capitais"]},
        "indice": {l: serie(l, "indice_base_2000") for l in caps + ["Brasil", "12 Capitais"]},
        "ranking": {l: serie(l, "ranking") for l in caps},
        "pct_brasil": {l: serie(l, "pct_brasil_calc") for l in caps + ["12 Capitais"]},
        "var_pct": {l: serie(l, "var_pct_anual") for l in caps},
        "resumo": res[res.tipo == "capital"][["localidade", "cursos_2000", "cursos_2022", "cagr_pct"]].round(3).to_dict("records"),
        "gini": [round(float(v), 4) for v in conc.gini],
    }
    (ASSETS / "data.js").write_text(
        "// Gerado por src/figures.py - não editar manualmente\nwindow.DATA = "
        + json.dumps(dados, ensure_ascii=False) + ";\n", encoding="utf-8")


def estatisticas_inferenciais(m, res):
    """Números citados no artigo (RQ3): convergência e correlações."""
    d = res[res.tipo == "capital"]
    rho, p = stats.spearmanr(d.cursos_2000, d.cagr_pct)
    r_log, p_log = stats.pearsonr(np.log(d.cursos_2000), d.cagr_pct)
    out = {"spearman_nivel_inicial_vs_cagr": [round(float(rho), 3), round(float(p), 4)],
           "pearson_logNivelInicial_vs_cagr": [round(float(r_log), 3), round(float(p_log), 4)],
           "n_capitais": int(len(d))}
    (PROC / "estatisticas_inferenciais.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    m, res, conc = carregar()
    fig1_evolucao(m); fig2_participacao(m); fig3_cagr(res)
    fig4_ranking(m); fig5_concentracao(conc); fig6_heatmap(m)
    exportar_data_js(m, res, conc)
    print(estatisticas_inferenciais(m, res))
    print("Figuras e data.js gerados em", ASSETS)


if __name__ == "__main__":
    main()
