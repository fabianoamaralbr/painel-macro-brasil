"""Análise Exploratória de Dados (EDA) — Painel Macro & Renda Fixa do Brasil.

Executa a análise ponta a ponta:
  1. baixa as séries do Banco Central (SGS);
  2. monta o painel diário e os índices acumulados;
  3. calcula as métricas de negócio;
  4. imprime um relatório legível no terminal;
  5. salva `notebooks/insights.json` para alimentar o README e o app.

Uso:  python notebooks/eda.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

# Permite rodar como script solto (python notebooks/eda.py) resolvendo o pacote src/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analysis import (  # noqa: E402
    indices_acumulados,
    juro_real,
    matriz_correlacao,
    montar_painel,
    resumo_insights,
)
from src.data import carregar_todas  # noqa: E402

INICIO = "2015-01-01"


def _pct(x: float) -> str:
    return f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    print("=" * 72)
    print("  EDA — PAINEL MACRO & RENDA FIXA DO BRASIL")
    print("  Fonte: Banco Central do Brasil (SGS)")
    print("=" * 72)

    print("\n[1/4] Baixando séries do SGS...")
    dados = carregar_todas(inicio=INICIO)
    for chave, serie in dados.items():
        print(f"    - {chave:12s}: {len(serie):>5d} obs  "
              f"({serie.index.min().date()} → {serie.index.max().date()})")

    print("\n[2/4] Montando painel diário e índices acumulados...")
    painel = montar_painel(dados)
    idx = indices_acumulados(dados)
    jr = juro_real(painel).dropna()
    print(f"    painel: {painel.shape[0]} linhas x {painel.shape[1]} colunas")

    print("\n[3/4] Estatísticas descritivas (painel diário):")
    with pd.option_context("display.width", 120, "display.max_columns", 20):
        print(painel.describe().round(2).to_string())

    print("\n    Matriz de correlação (variações diárias):")
    print(matriz_correlacao(painel).round(2).to_string())

    print("\n[4/4] Insights de negócio:")
    ins = resumo_insights(dados)
    p = ins["periodo"]
    print(f"""
    Período analisado: {p['inicio']} a {p['fim']}  (~{p['anos']} anos)

    JUROS E INFLAÇÃO
      • Selic (meta) atual .............. {_pct(ins['selic_atual'])}
      • IPCA 12 meses atual ............. {_pct(ins['ipca_12m_atual'])}
      • Juro real atual (ex-ante) ....... {_pct(ins['juro_real_atual'])}
      • Juro real médio no período ...... {_pct(ins['juro_real_medio'])}
      • Menor juro real ................. {_pct(ins['juro_real_min'])} em {ins['juro_real_min_data']}
      • Maior juro real ................. {_pct(ins['juro_real_max'])} em {ins['juro_real_max_data']}

    RENDA FIXA vs INFLAÇÃO (R$1 investido no CDI)
      • CDI acumulado (nominal) ......... {_pct(ins['cdi_acum_pct'])}
      • IPCA acumulado (inflação) ....... {_pct(ins['ipca_acum_pct'])}
      • Ganho REAL do CDI ............... {_pct(ins['cdi_real_acum_pct'])}

    CÂMBIO
      • Dólar: início R$ {ins['dolar_inicio']:.2f}  →  fim R$ {ins['dolar_fim']:.2f}
      • Pico: R$ {ins['dolar_max']:.2f} em {ins['dolar_max_data']}
      • Volatilidade anualizada ......... {_pct(ins['dolar_vol_anual'])}
      • Correlação Δmeta Selic × Δdólar . {ins['corr_selic_dolar']:.2f}
    """)

    saida = Path(__file__).resolve().parent / "insights.json"
    saida.write_text(json.dumps(ins, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"    → insights salvos em {saida}")
    print("=" * 72)


if __name__ == "__main__":
    main()
