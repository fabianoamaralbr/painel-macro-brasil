# Imagem enxuta e reprodutível para o dashboard Streamlit.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/app \
    PORT=8501

WORKDIR /app

# Instala dependências primeiro (melhor uso de cache de camadas).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do projeto.
COPY . .

# Hugging Face Spaces (e boas práticas) exigem execução como usuário não-root.
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

# Healthcheck usando o endpoint interno do Streamlit.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f\"http://localhost:{os.environ.get('PORT','8501')}/_stcore/health\")" || exit 1

# Respeita a variável PORT (Render, Railway etc.); default 8501 (Hugging Face).
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true"]
