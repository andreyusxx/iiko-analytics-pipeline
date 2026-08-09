FROM apache/superset:latest

USER root

# Встановлюємо системні залежності для роботи PostgreSQL
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Встановлюємо Python-драйвер глобально
RUN pip install --no-cache-dir psycopg2-binary

USER superset