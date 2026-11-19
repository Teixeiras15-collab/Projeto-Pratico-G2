# Expansão e desconcentração dos cursos de graduação presenciais nas 12 maiores capitais (2000–2022)

![Python](https://img.shields.io/badge/python-3.12-blue) ![License: MIT](https://img.shields.io/badge/code-MIT-green) ![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey) ![FAIR](https://img.shields.io/badge/FAIR-compliant-orange)

**Artigo (GitHub Pages):** https://SEU-USUARIO.github.io/cursos-graduacao-capitais/

| | |
|---|---|
| **Autores** | João Victor Teixeira · Renan Braga Gomes |
| **Instituição** | Faculdade UniLaSalle — Bacharelado em Sistemas de Informação, 6º período |
| **Disciplina** | Linguagem de Programação (Análise e Visualização de Dados com Python) |
| **Professor** | Alexandre Louzada |
| **Semestre** | 2026.2 |

## Resumo executivo
Pipeline reprodutível em Python que processa a **Tabela 913 do Data.Rio** (fonte: INEP) — cursos de graduação presenciais no Brasil e nas 12 maiores capitais, 2000–2022 — e comunica os resultados em um artigo HTML. Principais achados: oferta nacional de 10.585 → 35.765 cursos (+237,9%); expansão de 11,3% a.a. até 2009, 2,6% a.a. até 2019 e retração em 2020–2021; participação das capitais estável (≈ 26–29%) com degrau em 2009; desconcentração entre capitais (Gini 0,394 → 0,309); Rio de Janeiro com o menor CAGR (4,1% a.a.).

**Perguntas de pesquisa:** RQ1 evolução e inflexões · RQ2 participação e concentração · RQ3 ritmos por capital, convergência e caso do Rio.

**Palavras-chave:** ensino superior; cursos de graduação; capitais brasileiras; INEP; análise exploratória de dados; FAIR.

**Fonte original dos dados:** Data.Rio, *Tabela 913* — https://www.data.rio · INEP: http://www.inep.gov.br

## Estrutura
```
├── README.md · LICENSE · requirements.txt · .gitignore
├── data/
│   ├── raw/913.xls                  # arquivo bruto original (inalterado)
│   ├── processed/                   # csv.gz / csv / json (saída do ETL)
│   └── data_dictionary.md           # dicionário de variáveis
├── notebooks/analise_exploratoria.ipynb
├── src/etl.py                       # parsing, validação, métricas
├── src/figures.py                   # figuras PNG + docs/assets/data.js
└── docs/index.html (+ assets/)      # artigo publicado no GitHub Pages
```

## Como reproduzir
```bash
git clone https://github.com/SEU-USUARIO/cursos-graduacao-capitais.git
cd cursos-graduacao-capitais
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.etl         # lê data/raw/913.xls -> data/processed/
python -m src.figures     # gera docs/assets/ (PNG + data.js)
jupyter notebook notebooks/analise_exploratoria.ipynb
```
Visualizar o artigo localmente: abra `docs/index.html` (os gráficos interativos carregam Plotly.js por CDN, requer internet).

## Publicação no GitHub Pages
Settings → Pages → *Deploy from a branch* → branch `main`, pasta `/docs`.

## Garantias de qualidade do pipeline
Nenhuma operação destrutiva: o bruto fica intacto; abas descartadas, SHA-256 do bruto e checagens (nulos, duplicatas, soma das capitais = agregado, % oficial vs. recalculado) ficam em `data/processed/qa_report.json`.

## Licenças
Código: **MIT**. Dados derivados, texto e figuras: **CC BY 4.0**. Dados brutos: INEP/Data.Rio (condições da fonte).

## Como citar
TEIXEIRA, J. V.; GOMES, R. B. *Expansão e desconcentração dos cursos de graduação presenciais nas 12 maiores capitais brasileiras (2000–2022)*. Faculdade UniLaSalle, 2026.
