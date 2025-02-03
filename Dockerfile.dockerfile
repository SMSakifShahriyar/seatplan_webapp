Dockerfile
If you want to deploy using Docker (for example on Koyeb), here’s a basic Dockerfile.

dockerfile
Copy
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "app.py"]
