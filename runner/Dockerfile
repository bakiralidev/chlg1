FROM python:3.11-slim

WORKDIR /app

RUN groupadd --gid 10002 runneruser && \
    useradd --uid 10002 --gid 10002 --shell /bin/bash --create-home runneruser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN chown -R runneruser:runneruser /app
USER runneruser

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
