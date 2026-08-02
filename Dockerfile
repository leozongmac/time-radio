FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY time_radio ./time_radio

RUN pip install --no-cache-dir .

EXPOSE 8766

CMD ["uvicorn", "time_radio.main:app", "--host", "0.0.0.0", "--port", "8766", "--proxy-headers"]
