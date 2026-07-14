FROM python:3.11-slim

WORKDIR /app

COPY workers/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY workers/worker.py workers/memory.py workers/tools.py ./

CMD ["python", "worker.py"]
