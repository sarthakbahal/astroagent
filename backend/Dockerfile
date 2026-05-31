FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# flatlib==0.2.3 has an outdated hard-pin on pyswisseph==2.08.00-1.
# We install it without deps and rely on the wheel-backed pyswisseph pinned above.
RUN pip install --no-cache-dir --no-deps flatlib==0.2.3

COPY backend /app/backend

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
