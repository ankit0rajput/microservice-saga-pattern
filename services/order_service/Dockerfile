FROM python:3.11-slim

WORKDIR /app

COPY contracts ./contracts
COPY services/order_service ./services/order_service

RUN pip install --no-cache-dir -r services/order_service/requirements.txt

CMD ["uvicorn", "services.order_service.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
