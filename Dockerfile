# Use an official Python 3.9 slim image as the base
FROM python:3.9-slim

# Set environment variables to disable .pyc file generation and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the container
COPY . .

# Expose port 8000 (this is the port Gunicorn will use)
EXPOSE 8000

# Set environment variables for Flask (used by Gunicorn in production)
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Install Gunicorn for serving the Flask application
RUN pip install gunicorn

# Run the application using Gunicorn, binding to all network interfaces on port 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "app:app"]

