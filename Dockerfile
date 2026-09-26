FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY dataset ./dataset
COPY expanded ./expanded
COPY challenge-brief.md challenge-testing-brief.md engagement-design.md engagement-research.md ./
COPY examples ./examples
COPY docs ./docs
COPY scripts ./scripts
COPY submission.jsonl ./
COPY README.md ./

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
