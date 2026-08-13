# 📊 Painel Macro & Renda Fixa — Brasil

Dashboard interativo que consome **dados oficiais do Banco Central do Brasil** (SGS) e
transforma juros, inflação, renda fixa e câmbio em **insights de negócio**. Projeto de
portfólio de análise de dados, ponta a ponta: ingestão via API → análise em pandas →
app em Streamlit → containerização em Docker → deploy público gratuito.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.61-FF4B4B?logo=streamlit&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

> 🔗 **Demo pública:** _adicione aqui o link após o deploy_ (ex.: `https://fabianoamaralbr-painel-macro-brasil.hf.space`)

---

## 🎯 Sobre o projeto

O Brasil tem uma das taxas de juros reais mais altas do mundo e um câmbio historicamente
volátil. Este painel responde, com dado público e reproduzível, a perguntas que todo
investidor e gestor faz:

- O juro real está atrativo **agora** frente à própria história?
- A renda fixa pós-fixada (CDI) realmente **protege da inflação** no longo prazo?
- Quão volátil é o câmbio e o que ele tem a ver com a política de juros?

Toda a lógica analítica é centralizada em `src/analysis.py`, de modo que a **EDA** (script
de terminal) e o **dashboard** (Streamlit) usam exatamente os mesmos cálculos — sem
divergência entre o que se analisa e o que se publica.

---

## 💡 Principais insights

> Período analisado: **02/01/2015 a 12/08/2026 (~11,6 anos)**. Números recalculados a cada
> execução, direto da API — os valores abaixo refletem a última rodada.

| # | Insight | Número |
|---|---------|--------|
| 1 | **Juro real hoje está muito acima da média.** Elevado favorece pós-fixados e prefixados longos. | **9,15% a.a.** vs média de **4,26%** |
| 2 | **CDI bateu a inflação com folga.** R$100 no CDI viraram ~R$300 nominais em 11,6 anos. | Ganho **real de +61,1%** |
| 3 | **Já houve juro real negativo.** Em 08/2021 o dinheiro parado perdia da inflação. | **−4,95%** (mín.) |
| 4 | **Câmbio quase dobrou e é volátil.** Justifica hedge/diversificação em dólar. | R$2,69 → R$5,19 · vol. **14,5% a.a.** |
| 5 | **Câmbio não reage a juro no dia a dia.** Responde mais a fluxo global e risco. | ρ(ΔSelic, Δdólar) ≈ **−0,06** |

**Leitura de negócio:** o cenário atual (juro real ~9%, inflação ancorada perto de 4,4%)
é historicamente **favorável à renda fixa** — o custo de oportunidade de estar em caixa/
pós-fixado é baixo, enquanto o prêmio de ativos de risco precisa ser alto para competir.

---

## 🧱 Stack e arquitetura

```
API SGS/BCB  ──►  src/data.py      (ingestão + cache + fatiamento de janelas)
                  src/analysis.py  (juro real, índices acumulados, correlações)
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
   notebooks/eda.py          app.py (Streamlit)
   (relatório + insights.json)   (dashboard interativo)
                        │
                        ▼
                   Docker  ──►  Hugging Face Spaces / Render (link público)
```

- **Python 3.12**, **pandas**, **NumPy**
- **Streamlit** (app) + **Plotly** (gráficos)
- **requests** (API REST do Banco Central)
- **Docker** para empacotamento reprodutível

---

## 📂 Estrutura

```
painel-macro-brasil/
├── app.py                  # dashboard Streamlit
├── src/
│   ├── data.py             # ingestão das séries do SGS (com cache e retry)
│   └── analysis.py         # métricas de negócio (única fonte de verdade)
├── notebooks/
│   ├── eda.py              # análise exploratória por linha de comando
│   └── insights.json       # números da última rodada (gerado pela EDA)
├── .streamlit/config.toml  # tema visual
├── Dockerfile              # imagem de produção
├── requirements.txt
└── README.md
```

---

## 🗄️ Fontes de dados (Banco Central — SGS)

Todas as séries são públicas, sem autenticação, via API REST do
[Sistema Gerenciador de Séries Temporais](https://www3.bcb.gov.br/sgspub/).

| Série | Código SGS | Uso |
|-------|-----------|-----|
| Meta Selic (% a.a.) | 432 | Juro básico / referência |
| CDI (% ao dia) | 12 | Índice de renda fixa acumulada |
| IPCA (% no mês) | 433 | Inflação acumulada |
| IPCA acumulado 12m (% a.a.) | 13522 | Juro real e KPI de inflação |
| IGP-M (% no mês) | 189 | Inflação alternativa |
| Dólar PTAX compra (R$/US$) | 1 | Câmbio |

---

## ▶️ Como rodar localmente

Pré-requisito: Python 3.12+.

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. (Opcional) rodar a EDA no terminal — imprime o relatório e gera insights.json
python notebooks/eda.py

# 3. Subir o dashboard
streamlit run app.py
```

O app abre em `http://localhost:8501`. A primeira carga baixa as séries do Banco Central
(alguns segundos) e mantém em cache por 6 horas.

---

## 🐳 Como rodar com Docker

```bash
# Build da imagem
docker build -t painel-macro-brasil .

# Rodar (expõe na porta 8501)
docker run -p 8501:8501 painel-macro-brasil
```

Acesse `http://localhost:8501`. A imagem respeita a variável de ambiente `PORT`, o que a
torna compatível com plataformas que injetam a porta (Render, Railway etc.).

---

## 🌐 Como publicar um link público (gratuito)

### Opção A — Hugging Face Spaces (Docker) · **recomendada**

Usa o `Dockerfile` do projeto e entrega uma URL pública fixa, de graça.

1. Crie um Space em **https://huggingface.co/new-space** → **SDK: Docker** → *Blank*.
   Nome sugerido: `painel-macro-brasil`.
2. Envie os arquivos do projeto para o repositório do Space:
   ```bash
   git clone https://huggingface.co/spaces/fabianoamaralbr/painel-macro-brasil
   cd painel-macro-brasil
   # copie para cá todos os arquivos deste projeto, depois:
   git add .
   git commit -m "deploy do painel macro"
   git push
   ```
3. **Importante:** o Hugging Face precisa de metadados no topo do `README.md` do Space.
   Cole este bloco como as **primeiras linhas** do README lá:
   ```yaml
   ---
   title: Painel Macro Renda Fixa Brasil
   emoji: 📊
   colorFrom: blue
   colorTo: indigo
   sdk: docker
   app_port: 8501
   pinned: false
   ---
   ```
4. O build roda sozinho. URL pública: `https://fabianoamaralbr-painel-macro-brasil.hf.space`

### Opção B — Streamlit Community Cloud (sem Docker, ainda mais simples)

1. Suba este projeto para um repositório no GitHub.
2. Acesse **https://share.streamlit.io** → *New app* → selecione o repositório,
   branch `main`, arquivo `app.py` → **Deploy**.
3. URL pública: `https://<seu-app>.streamlit.app`.

### Opção C — Render (Docker)

1. Suba o projeto para o GitHub.
2. Em **https://render.com** → *New* → *Web Service* → conecte o repositório →
   ambiente **Docker** → plano **Free**.
3. Render injeta `PORT` automaticamente (o `Dockerfile` já trata isso).
   URL pública: `https://<seu-app>.onrender.com`. *(No plano free o serviço hiberna após
   inatividade e demora alguns segundos para acordar.)*

---

## 🧮 Metodologia

- **Juro real (ex-ante):** `(1 + Selic) / (1 + IPCA 12m) − 1`. É a taxa de Fisher, mais
  precisa que a subtração simples Selic − IPCA.
- **CDI acumulado:** produto dos fatores diários `∏ (1 + CDI_dia/100)`, base 100.
- **Inflação acumulada:** produto dos fatores mensais do IPCA, reindexado ao calendário
  diário para comparação direta com o CDI.
- **CDI real:** CDI acumulado dividido pela inflação acumulada — o ganho de poder de compra.
- **Volatilidade cambial:** desvio-padrão dos retornos logarítmicos diários, anualizado
  por `√252`.

---

## ⚠️ Aviso

Projeto **educacional e analítico**, construído com dados públicos. **Não constitui
recomendação de investimento.**

---

## 👤 Autor

**Fabiano Amaral** — análise de dados
GitHub: [@fabianoamaralbr](https://github.com/fabianoamaralbr)

Licença: [MIT](LICENSE).
