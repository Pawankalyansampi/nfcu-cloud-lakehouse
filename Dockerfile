FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY dbt ./dbt
COPY data/knowledge ./data/knowledge
COPY scripts ./scripts
COPY run_local.py docker_api.py ./

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000 8501

CMD ["python", "docker_api.py"]
