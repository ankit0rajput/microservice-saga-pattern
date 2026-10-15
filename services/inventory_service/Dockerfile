FROM python:3.11-slim

WORKDIR /app

COPY contracts ./contracts
COPY services/inventory_service ./services/inventory_service

RUN pip install --no-cache-dir -r services/inventory_service/requirements.txt

CMD ["uvicorn", "services.inventory_service.app.main:app", "--host", "0.0.0.0", "--port", "8002"]
