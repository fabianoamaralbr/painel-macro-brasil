"""Transformações e métricas de negócio sobre as séries do Banco Central.

Toda a lógica analítica vive aqui para que tanto a EDA (notebooks/eda.py) quanto o
app Streamlit (app.py) consumam exatamente os mesmos cálculos — sem divergência.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DIAS_UTEIS_ANO = 252


def montar_painel(dados: dict[str, pd.Series]) -> pd.DataFrame:
    """Une todas as séries em um DataFrame diário.

    Séries mensais (IPCA, IGP-M) são propagadas para frente (ffill), de modo que cada
    dia carrega o último dado divulgado — o comportamento correto para um painel de
    acompanhamento, em que uma métrica mensal vale até a próxima divulgação.
    """
    df = pd.DataFrame({chave: serie for chave, serie in dados.items()})
    df = df.sort_index()
    # Preenche as séries lentas (mensais) para frente; mantém as diárias como estão.
    mensais = ["ipca_mes", "ipca_12m", "igpm_mes"]
    df[mensais] = df[mensais].ffill()
    df["selic_meta"] = df["selic_meta"].ffill()  # meta só muda em reunião do Copom
    return df


def indices_acumulados(dados: dict[str, pd.Series]) -> pd.DataFrame:
    """Constrói índices base 100 de um R$1 investido no CDI e do IPCA (inflação).

    - CDI: produto acumulado dos fatores diários (1 + cdi_dia/100).
    - IPCA: produto acumulado dos fatores mensais (1 + ipca_mes/100), reindexado ao diário.
    Ambos rebaseados a 100 na primeira data em comum.
    """
    cdi = dados["cdi_dia"].dropna()
    fator_cdi = (1 + cdi / 100).cumprod()

    ipca = dados["ipca_mes"].dropna()
    fator_ipca = (1 + ipca / 100).cumprod()

    # Alinha tudo no calendário diário do CDI.
    fator_ipca_diario = fator_ipca.reindex(fator_cdi.index, method="ffill")

    base = pd.DataFrame({"cdi": fator_cdi, "ipca": fator_ipca_diario}).dropna()
    base = base / base.iloc[0] * 100  # rebaseia a 100
    base["cdi_real"] = base["cdi"] / base["ipca"] * 100  # CDI descontada a inflação
    return base


def juro_real(painel: pd.DataFrame) -> pd.Series:
    """Juro real ex-ante aproximado: (1+Selic)/(1+IPCA 12m) - 1, em % a.a."""
    selic = painel["selic_meta"] / 100
    ipca12 = painel["ipca_12m"] / 100
    return ((1 + selic) / (1 + ipca12) - 1) * 100


def volatilidade_anual(serie: pd.Series) -> float:
    """Volatilidade anualizada dos retornos diários (ex.: câmbio)."""
    ret = np.log(serie / serie.shift(1)).dropna()
    return float(ret.std() * np.sqrt(DIAS_UTEIS_ANO) * 100)


def matriz_correlacao(painel: pd.DataFrame) -> pd.DataFrame:
    """Correlação entre variações diárias das principais variáveis do painel."""
    cols = {
        "Selic meta": painel["selic_meta"],
        "IPCA 12m": painel["ipca_12m"],
        "Dólar": painel["dolar"],
        "CDI diário": painel["cdi_dia"],
    }
    variacoes = pd.DataFrame(cols).diff()
    return variacoes.corr()


def resumo_insights(dados: dict[str, pd.Series]) -> dict:
    """Consolida os números de negócio usados nos cartões da EDA e do dashboard."""
    painel = montar_painel(dados)
    idx = indices_acumulados(dados)
    jr = juro_real(painel).dropna()

    inicio = idx.index.min()
    fim = idx.index.max()
    anos = (fim - inicio).days / 365.25

    cdi_total = idx["cdi"].iloc[-1] / 100 - 1          # retorno nominal acumulado do CDI
    ipca_total = idx["ipca"].iloc[-1] / 100 - 1        # inflação acumulada
    cdi_real_total = idx["cdi_real"].iloc[-1] / 100 - 1  # ganho real acumulado do CDI

    return {
        "periodo": {"inicio": inicio.strftime("%d/%m/%Y"), "fim": fim.strftime("%d/%m/%Y"),
                     "anos": round(anos, 1)},
        "selic_atual": float(painel["selic_meta"].dropna().iloc[-1]),
        "ipca_12m_atual": float(painel["ipca_12m"].dropna().iloc[-1]),
        "juro_real_atual": float(jr.iloc[-1]),
        "juro_real_medio": float(jr.mean()),
        "juro_real_min": float(jr.min()),
        "juro_real_min_data": jr.idxmin().strftime("%m/%Y"),
        "juro_real_max": float(jr.max()),
        "juro_real_max_data": jr.idxmax().strftime("%m/%Y"),
        "cdi_acum_pct": float(cdi_total * 100),
        "ipca_acum_pct": float(ipca_total * 100),
        "cdi_real_acum_pct": float(cdi_real_total * 100),
        "dolar_inicio": float(painel["dolar"].dropna().iloc[0]),
        "dolar_fim": float(painel["dolar"].dropna().iloc[-1]),
        "dolar_max": float(painel["dolar"].max()),
        "dolar_max_data": painel["dolar"].idxmax().strftime("%m/%Y"),
        "dolar_vol_anual": volatilidade_anual(painel["dolar"].dropna()),
        "corr_selic_dolar": float(matriz_correlacao(painel).loc["Selic meta", "Dólar"]),
    }
