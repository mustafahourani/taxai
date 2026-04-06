FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV ANTHROPIC_MODEL=claude-opus-4-6
ENV USE_MOCK_AI=true
ENV EIGENCOMPUTE_TEE=false

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
