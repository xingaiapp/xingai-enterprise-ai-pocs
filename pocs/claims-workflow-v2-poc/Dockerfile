FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY claims_workflow ./claims_workflow

EXPOSE 8091

CMD ["uvicorn", "claims_workflow.api.main:app", "--host", "0.0.0.0", "--port", "8091"]
