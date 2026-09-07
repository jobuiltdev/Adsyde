FROM python:3.13.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY config ./config
COPY apps ./apps
COPY tests ./tests
COPY manage.py ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir ".[dev]"
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

