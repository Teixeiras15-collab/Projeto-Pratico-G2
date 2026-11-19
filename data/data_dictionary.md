# Dicionário de Dados

**Fonte:** INEP — Cadastro das Instituições de Educação Superior / Sinopse do Censo da Educação Superior, via **Data.Rio** (Prefeitura do Rio de Janeiro), *Tabela 913 – Ensino Superior – Número e distribuição percentual dos cursos de graduação presenciais – Brasil e suas 12 maiores capitais*.
**Cobertura:** 2000–2022 (anual) · **Granularidade:** ano × localidade (Brasil, agregado de 12 capitais e 12 capitais individuais) · **Unidade de contagem:** cursos de graduação presenciais.
**Licença dos dados derivados:** CC BY 4.0.

## Dados brutos — `data/raw/913.xls`
Uma aba por ano (`2000` … `2022`) + aba técnica `ESRI_MAPINFO_SHEET` (vazia, descartada e registrada no `qa_report.json`). Cada aba tem cabeçalho institucional, tabela (colunas `Capitais`, `Total`, `%`) e rodapé com a fonte. A ordem das capitais muda a cada ano (ordenadas por número de cursos).

## `cursos_graduacao_long.csv.gz` (322 linhas = 23 anos × 14 localidades)

| Variável | Tipo | Formato / Unidade | Descrição |
|---|---|---|---|
| `ano` | int | AAAA | Ano de referência do censo/cadastro. |
| `localidade` | string | texto | `Brasil`, `12 Capitais` (agregado) ou nome da capital. |
| `tipo` | string | `nacional` \| `agregado` \| `capital` | Nível da linha. Evita dupla contagem ao somar. |
| `total_cursos` | Int64 | contagem (cursos) | Nº de cursos de graduação presenciais. Em 2022 veio como texto com espaço de milhar (`"35 765"`) e foi convertido. |
| `pct_oficial` | float | % (0–100) | Percentual **publicado** da localidade sobre o Brasil. 2022 vem com 1 casa decimal. |

## `metricas_capitais.csv.gz` (mesmas linhas + métricas derivadas)

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `pct_brasil_calc` | float | % | `total_cursos / total do Brasil × 100`, recalculado (erro máx. vs. oficial: 0,0495 p.p., só arredondamento). |
| `pct_nas_12_capitais` | float | % | Fatia da capital no agregado das 12 capitais (nulo para Brasil/agregado). |
| `var_abs_anual` | float | cursos | Diferença para o ano anterior (nulo em 2000). |
| `var_pct_anual` | float | % | Variação percentual anual (nulo em 2000). |
| `indice_base_2000` | float | índice (2000 = 100) | Valor da série / valor em 2000 × 100. |
| `ranking` | Int64 | 1–12 | Posição da capital no ano (1 = mais cursos; empate = menor posição). Nulo para Brasil/agregado. |

(demais colunas herdadas de `cursos_graduacao_long`.)

## Tabelas auxiliares

- **`resumo_por_localidade.csv`**: `cursos_2000`, `cursos_2022`, `var_abs`, `var_pct_total`, `cagr_pct` (crescimento composto anual, % a.a.), `ano_pico`, `cursos_pico`, `var_pct_desde_pico`, `rank_2000`, `rank_2022`, `pct_brasil_2000`, `pct_brasil_2022`.
- **`indicadores_concentracao.csv`** (por ano, entre as 12 capitais): `media`, `mediana`, `desvio_padrao`, `cv` (coef. de variação), `hhi` (Herfindahl-Hirschman, 0–10.000), `gini` (0–1), `pct_top1_nas_12` (fatia da maior capital), `pct_12_capitais_no_brasil`.
- **`outliers_variacao_anual.csv`**: variações anuais com z-score robusto (mediana/MAD) ≥ 3,5 em módulo, por série.
- **`proveniencia_abas.csv`**: título e nota de fonte originais de cada aba (a fonte INEP muda ao longo da série).
- **`qa_report.json`**: relatório de validação (nulos, duplicatas, soma das capitais = agregado, SHA-256 do arquivo bruto, abas descartadas).
- **`estatisticas_inferenciais.json`**: correlações citadas no artigo.

## Limitações conhecidas
1. A unidade é **curso**, não vagas, matrículas ou instituições.
2. Apenas modalidade **presencial** (exclui EAD).
3. As "12 maiores capitais" são um recorte fixo; capitais menores não aparecem.
4. A fonte do INEP e a data de acesso variam entre abas; possíveis revisões metodológicas (ex.: salto nacional em 2009) não são documentadas na planilha.
