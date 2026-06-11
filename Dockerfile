# Painel Financeiro 3 Amores — imagem Docker (Python 3.12 + Streamlit + Firebird client)
FROM python:3.12-slim

WORKDIR /app

# Firebird 4 client library (para conexão direta ao ERP Auditor)
# libfbclient2 = cliente Firebird 3/4 — protocolo wire compatível com Firebird 4 server
RUN apt-get update && apt-get install -y --no-install-recommends \
        libfbclient2 \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python (camada cacheável — só reinstala se requirements mudar)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código + de-para template + config do Streamlit
# (os DADOS e SENHAS NÃO entram na imagem — vêm do volume /dados via PAINEL_DADOS)
COPY app/ ./app/
COPY tools/ ./tools/
COPY config/ ./config/
COPY .streamlit/ ./.streamlit/

ENV PAINEL_DADOS=/dados
# Caminho do client Firebird no Linux (Debian bookworm via libfbclient2)
ENV FB_CLIENT_LIBRARY=libfbclient.so.2

EXPOSE 8501

# Healthcheck nativo do Streamlit
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health').read()==b'ok' else 1)" || exit 1

CMD ["python", "-m", "streamlit", "run", "app/painel.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
