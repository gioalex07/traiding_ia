FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd --system --gid 10001 rac \
    && useradd --system --uid 10001 --gid 10001 --create-home rac

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=rac:rac rac ./rac
COPY --chown=rac:rac db ./db
COPY --chown=rac:rac tests ./tests

USER 10001:10001

FROM base AS api
CMD ["python", "-m", "uvicorn", "rac.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS worker
CMD ["python", "-m", "rac.worker.loop"]

FROM base AS scheduler
CMD ["python", "-c", "import time; print('rac scheduler placeholder'); time.sleep(3600)"]
