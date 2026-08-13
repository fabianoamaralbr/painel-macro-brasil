"""Painel Macro & Renda Fixa do Brasil — dashboard interativo em Streamlit.

Consome as séries do Banco Central (SGS), calcula métricas de negócio e apresenta
juros, inflação, renda fixa e câmbio de forma navegável.

Rodar local:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis import (
    indices_acumulados,
    juro_real,
    matriz_correlacao,
    montar_painel,
    resumo_insights,
)
from src.data import carregar_todas

# ---------------------------------------------------------------------------
# Configuração da página + tema visual (paleta neutra, sem qualquer marca)
# ---------------------------------------------------------------------------
COR_FUNDO = "#0b1220"
COR_PAINEL = "#16202e"
COR_TEXTO = "#e6edf3"
COR_SELIC = "#38bdf8"   # azul-céu
COR_IPCA = "#fbbf24"    # âmbar
COR_CDI = "#34d399"     # verde-água
COR_REAL = "#a78bfa"    # violeta
COR_DOLAR = "#f472b6"   # rosa
COR_NEG = "#ef4444"     # vermelho

st.set_page_config(
    page_title="Painel Macro & Renda Fixa — Brasil",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
      html, body, [class*="css"], .stMarkdown, .stMetric { font-family: 'Inter', sans-serif; }
      .bloco-insight {
          background: #16202e; border-left: 4px solid #38bdf8; border-radius: 8px;
          padding: 16px 18px; margin: 6px 0 18px 0; color: #cbd5e1; font-size: 0.95rem;
      }
      .bloco-insight b { color: #e6edf3; }
      h1, h2, h3 { font-family: 'Inter', sans-serif; font-weight: 800; letter-spacing: -0.02em; }
      [data-testid="stMetricValue"] { font-weight: 800; }
      footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


def estilizar(fig: go.Figure, altura: int = 420) -> go.Figure:
    """Aplica o tema escuro consistente a qualquer figura Plotly."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COR_FUNDO,
        plot_bgcolor=COR_FUNDO,
        font=dict(family="Inter, sans-serif", color=COR_TEXTO, size=13),
        height=altura,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#22303f", zeroline=False)
    fig.update_yaxes(gridcolor="#22303f", zeroline=False)
    return fig


# ---------------------------------------------------------------------------
# Carga de dados (cache de 6h para não bater na API a cada interação)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60 * 60 * 6, show_spinner="Baixando séries do Banco Central...")
def obter_dados(inicio: str) -> dict[str, pd.Series]:
    return carregar_todas(inicio=inicio, usar_cache=False)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Parâmetros")
    ano_inicio = st.select_slider(
        "Início da série",
        options=list(range(2015, 2027)),
        value=2015,
        help="Ano a partir do qual as séries do Banco Central são carregadas.",
    )
    st.caption("Fonte: **Banco Central do Brasil** — Sistema Gerenciador de "
               "Séries Temporais (SGS). Dados públicos, atualização diária.")
    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Projeto de portfólio · análise de dados\n\n"
               "Autor: **Fabiano Amaral** · GitHub [@fabianoamaralbr](https://github.com/fabianoamaralbr)")

try:
    dados = obter_dados(f"{ano_inicio}-01-01")
except Exception as exc:  # noqa: BLE001
    st.error(f"Não foi possível carregar os dados do Banco Central agora. Detalhe: {exc}")
    st.stop()

painel = montar_painel(dados)
idx = indices_acumulados(dados)
jr = juro_real(painel).dropna()
ins = resumo_insights(dados)

# ---------------------------------------------------------------------------
# Cabeçalho + KPIs
# ---------------------------------------------------------------------------
st.title("Painel Macro & Renda Fixa — Brasil 🇧🇷")
st.markdown(
    f"Juros, inflação, renda fixa e câmbio a partir de dados oficiais do "
    f"**Banco Central**. Período: **{ins['periodo']['inicio']} a "
    f"{ins['periodo']['fim']}** (~{ins['periodo']['anos']} anos)."
)

selic = painel["selic_meta"].dropna()
ipca12 = painel["ipca_12m"].dropna()
dolar = painel["dolar"].dropna()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Selic (meta)", f"{ins['selic_atual']:.2f}%",
          f"{selic.iloc[-1] - selic.iloc[-min(252, len(selic))]:+.2f} p.p. (12m)")
k2.metric("IPCA 12 meses", f"{ins['ipca_12m_atual']:.2f}%",
          f"{ipca12.iloc[-1] - ipca12.iloc[-min(252, len(ipca12))]:+.2f} p.p. (12m)",
          delta_color="inverse")
k3.metric("Juro real (ex-ante)", f"{ins['juro_real_atual']:.2f}%",
          f"média {ins['juro_real_medio']:.2f}%", delta_color="off")
k4.metric("Dólar (PTAX)", f"R$ {ins['dolar_fim']:.2f}",
          f"{(dolar.iloc[-1]/dolar.iloc[-min(252, len(dolar))]-1)*100:+.1f}% (12m)",
          delta_color="inverse")

st.divider()

# ---------------------------------------------------------------------------
# Abas de análise
# ---------------------------------------------------------------------------
aba1, aba2, aba3, aba4 = st.tabs(
    ["📈 Juros & Inflação", "💰 Renda Fixa vs Inflação", "💵 Câmbio", "🔗 Correlações"]
)

# --- Aba 1: Juros & Inflação ------------------------------------------------
with aba1:
    fig = go.Figure()
    fig.add_scatter(x=selic.index, y=selic, name="Selic meta (% a.a.)",
                    line=dict(color=COR_SELIC, width=2.5))
    fig.add_scatter(x=ipca12.index, y=ipca12, name="IPCA 12m (% a.a.)",
                    line=dict(color=COR_IPCA, width=2.5))
    fig.update_layout(title="Selic × Inflação (IPCA 12 meses)")
    st.plotly_chart(estilizar(fig), use_container_width=True)

    figjr = go.Figure()
    figjr.add_scatter(x=jr.index, y=jr, name="Juro real (% a.a.)", fill="tozeroy",
                      line=dict(color=COR_CDI, width=2))
    figjr.add_hline(y=0, line_dash="dash", line_color=COR_NEG)
    figjr.update_layout(title="Juro real ex-ante — (1+Selic)/(1+IPCA 12m) − 1")
    st.plotly_chart(estilizar(figjr, 360), use_container_width=True)

    st.markdown(
        f"""<div class="bloco-insight">
        <b>Insight.</b> O juro real atual é de <b>{ins['juro_real_atual']:.2f}% a.a.</b>,
        bem acima da média histórica de {ins['juro_real_medio']:.2f}%. Em
        {ins['juro_real_min_data']} o juro real chegou a <b>{ins['juro_real_min']:.2f}%</b>
        (negativo — dinheiro parado perdia da inflação); hoje a renda fixa pós-fixada
        está entre as mais atrativas do período. Juro real elevado favorece alocação em
        pós-fixados e prefixados longos, e tende a pressionar ativos de risco.
        </div>""",
        unsafe_allow_html=True,
    )

# --- Aba 2: Renda Fixa vs Inflação -----------------------------------------
with aba2:
    fig = go.Figure()
    fig.add_scatter(x=idx.index, y=idx["cdi"], name="CDI acumulado (nominal)",
                    line=dict(color=COR_CDI, width=2.5))
    fig.add_scatter(x=idx.index, y=idx["ipca"], name="IPCA acumulado (inflação)",
                    line=dict(color=COR_IPCA, width=2.5))
    fig.add_scatter(x=idx.index, y=idx["cdi_real"], name="CDI real (descontada inflação)",
                    line=dict(color=COR_REAL, width=2.5, dash="dot"))
    fig.update_layout(title="R$100 investidos no CDI vs inflação (base 100)")
    st.plotly_chart(estilizar(fig), use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("CDI acumulado", f"{ins['cdi_acum_pct']:.1f}%")
    c2.metric("Inflação (IPCA)", f"{ins['ipca_acum_pct']:.1f}%")
    c3.metric("Ganho real do CDI", f"{ins['cdi_real_acum_pct']:.1f}%")

    st.markdown(
        f"""<div class="bloco-insight">
        <b>Insight.</b> No período, R$100 no CDI viraram
        <b>R$ {100*(1+ins['cdi_acum_pct']/100):.0f}</b> (nominal), enquanto a inflação
        acumulou {ins['ipca_acum_pct']:.1f}%. O <b>ganho real de
        {ins['cdi_real_acum_pct']:.1f}%</b> mostra que o CDI protegeu e ainda ampliou o
        poder de compra — o argumento central da renda fixa pós-fixada no Brasil.
        </div>""",
        unsafe_allow_html=True,
    )

# --- Aba 3: Câmbio ----------------------------------------------------------
with aba3:
    fig = go.Figure()
    fig.add_scatter(x=dolar.index, y=dolar, name="Dólar PTAX (R$/US$)",
                    line=dict(color=COR_DOLAR, width=2.5))
    fig.update_layout(title="Cotação do dólar (PTAX compra)")
    st.plotly_chart(estilizar(fig), use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Dólar hoje", f"R$ {ins['dolar_fim']:.2f}")
    c2.metric("Pico do período", f"R$ {ins['dolar_max']:.2f}", ins["dolar_max_data"],
              delta_color="off")
    c3.metric("Volatilidade anual", f"{ins['dolar_vol_anual']:.1f}%")

    st.markdown(
        f"""<div class="bloco-insight">
        <b>Insight.</b> O dólar saiu de R$ {ins['dolar_inicio']:.2f} para
        R$ {ins['dolar_fim']:.2f}, com pico de R$ {ins['dolar_max']:.2f} em
        {ins['dolar_max_data']} e volatilidade anualizada de
        <b>{ins['dolar_vol_anual']:.1f}%</b>. Essa oscilação justifica hedge cambial em
        carteiras com passivos ou objetivos em dólar e reforça a diversificação
        internacional.
        </div>""",
        unsafe_allow_html=True,
    )

# --- Aba 4: Correlações -----------------------------------------------------
with aba4:
    corr = matriz_correlacao(painel)
    fig = go.Figure(data=go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index, zmin=-1, zmax=1,
        colorscale="RdBu", reversescale=True,
        text=corr.round(2).values, texttemplate="%{text}",
        colorbar=dict(title="ρ"),
    ))
    fig.update_layout(title="Correlação entre variações diárias")
    st.plotly_chart(estilizar(fig, 460), use_container_width=True)

    st.markdown(
        f"""<div class="bloco-insight">
        <b>Insight.</b> A correlação entre variações da meta Selic e do dólar é
        <b>{ins['corr_selic_dolar']:.2f}</b> — próxima de zero no dia a dia: câmbio
        responde muito mais a fluxo global e risco do que a movimentos pontuais de juro.
        Já Selic e CDI andam praticamente colados (ρ ≈ 1), como esperado, pois o CDI
        acompanha a taxa básica.
        </div>""",
        unsafe_allow_html=True,
    )

st.divider()
st.caption(
    "Dados: Banco Central do Brasil (SGS) · séries 432, 12, 433, 13522, 189 e 1. "
    "Conteúdo educacional/analítico — não constitui recomendação de investimento."
)
