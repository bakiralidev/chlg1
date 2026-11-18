FROM python:3.11-slim

WORKDIR /app

RUN groupadd --gid 10001 botuser && \
    useradd --uid 10001 --gid 10001 --shell /bin/bash --create-home botuser

COPY bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY bot /app/bot

RUN chown -R botuser:botuser /app
USER botuser

ENV PYTHONPATH=/app:/backend
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "bot.main"]
