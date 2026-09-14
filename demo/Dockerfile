FROM python:3.12-slim
WORKDIR /app
COPY requirements-cloud.txt /app/requirements-cloud.txt
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY orders /app/orders
COPY scripts /app/scripts
COPY sql /app/sql
COPY infra/modules/orders/orders-schema.json /app/infra/modules/orders/orders-schema.json
COPY demo /app/demo
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "demo.batch"]
