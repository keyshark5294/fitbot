FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker-entrypoint.sh

# entrypoint прогоняет alembic upgrade head, затем запускает бота
ENTRYPOINT ["./docker-entrypoint.sh"]
