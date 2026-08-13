"""Ingestão de séries do SGS (Sistema Gerenciador de Séries Temporais) do Banco Central.

O SGS expõe uma API REST pública e sem autenticação. Cada série tem um código numérico.
Documentação: https://www3.bcb.gov.br/sgspub/

Observação importante: para séries diárias o SGS limita cada requisição a ~10 anos.
Por isso `fetch_serie` fatia o intervalo em janelas menores e concatena o resultado.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

# Séries do SGS usadas no painel macro / renda fixa.
# freq: "D" diária, "M" mensal (define como a série é preenchida no painel diário).
SERIES: dict[str, dict] = {
    "selic_meta": {"codigo": 432,   "nome": "Meta Selic (% a.a.)",         "freq": "D"},
    "cdi_dia":    {"codigo": 12,    "nome": "CDI (% ao dia)",              "freq": "D"},
    "ipca_mes":   {"codigo": 433,   "nome": "IPCA (% no mês)",            "freq": "M"},
    "ipca_12m":   {"codigo": 13522, "nome": "IPCA acumulado 12m (% a.a.)", "freq": "M"},
    "igpm_mes":   {"codigo": 189,   "nome": "IGP-M (% no mês)",           "freq": "M"},
    "dolar":      {"codigo": 1,     "nome": "Dólar PTAX compra (R$/US$)",  "freq": "D"},
}

CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DIR.mkdir(exist_ok=True)


def _parse(payload: list[dict]) -> pd.Series:
    """Converte o JSON do SGS ([{data, valor}, ...]) em uma Series indexada por data."""
    df = pd.DataFrame(payload)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df.set_index("data")["valor"].sort_index()


def _fetch_janela(codigo: int, inicio: pd.Timestamp, fim: pd.Timestamp,
                  timeout: int = 30, tentativas: int = 3) -> pd.Series:
    """Busca uma única janela de datas de uma série, com retry e backoff."""
    params = {
        "formato": "json",
        "dataInicial": inicio.strftime("%d/%m/%Y"),
        "dataFinal": fim.strftime("%d/%m/%Y"),
    }
    url = SGS_URL.format(codigo=codigo)
    erro = None
    for i in range(tentativas):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            dados = resp.json()
            return _parse(dados) if dados else pd.Series(dtype="float64")
        except Exception as exc:  # noqa: BLE001 - queremos tolerar qualquer falha de rede
            erro = exc
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"Falha ao buscar série {codigo} ({inicio.date()}–{fim.date()}): {erro}")


def fetch_serie(codigo: int, inicio: str = "2015-01-01", fim: str | None = None,
                usar_cache: bool = True) -> pd.Series:
    """Busca uma série completa do SGS, fatiando em janelas de 9 anos e usando cache local.

    Parameters
    ----------
    codigo : int          código da série no SGS
    inicio : str          data inicial (YYYY-MM-DD)
    fim : str | None      data final (YYYY-MM-DD); default = hoje
    usar_cache : bool     se True, lê/grava um CSV em ``data/`` para evitar rebaixar tudo
    """
    ini = pd.Timestamp(inicio)
    fim_ts = pd.Timestamp(fim) if fim else pd.Timestamp.today().normalize()

    cache = CACHE_DIR / f"sgs_{codigo}.csv"
    if usar_cache and cache.exists():
        s = pd.read_csv(cache, index_col=0, parse_dates=True)["valor"]
        if s.index.min() <= ini and s.index.max() >= fim_ts - pd.Timedelta(days=7):
            return s.loc[ini:fim_ts]

    partes: list[pd.Series] = []
    cursor = ini
    while cursor <= fim_ts:
        janela_fim = min(cursor + pd.DateOffset(years=9) - pd.Timedelta(days=1), fim_ts)
        partes.append(_fetch_janela(codigo, cursor, janela_fim))
        cursor = janela_fim + pd.Timedelta(days=1)

    serie = pd.concat(partes)
    serie = serie[~serie.index.duplicated(keep="first")].sort_index()

    if usar_cache:
        serie.rename("valor").to_frame().to_csv(cache)
    return serie.loc[ini:fim_ts]


def carregar_todas(inicio: str = "2015-01-01", fim: str | None = None,
                   usar_cache: bool = True) -> dict[str, pd.Series]:
    """Baixa todas as séries de ``SERIES`` e devolve um dicionário chave -> Series."""
    saida: dict[str, pd.Series] = {}
    for chave, meta in SERIES.items():
        saida[chave] = fetch_serie(meta["codigo"], inicio, fim, usar_cache=usar_cache)
    return saida
