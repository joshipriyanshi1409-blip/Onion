FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYAaZSCAN_DATA_DIR=/app/data/runtime
WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY ml ./ml
COPY training ./training
COPY research ./research
COPY frontend ./frontend
COPY data/demo ./data/demo
COPY docs ./docs
COPY README.md ./README.md

RUN mkdir -p /app/data/runtime
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
