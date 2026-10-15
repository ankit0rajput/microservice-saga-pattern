FROM python:3.11-slim

WORKDIR /app

COPY contracts ./contracts
COPY services/payment_service ./services/payment_service

RUN pip install --no-cache-dir -r services/payment_service/requirements.txt

CMD ["uvicorn", "services.payment_service.app.main:app", "--host", "0.0.0.0", "--port", "8003"]
