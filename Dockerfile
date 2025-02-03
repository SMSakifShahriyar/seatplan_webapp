# Use an official Python 3.9 slim image as the base
FROM python:3.9-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the container
COPY . .

# Expose port 8000 for the application
EXPOSE 8000

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Install Gunicorn for production serving
RUN pip install gunicorn

# Use Gunicorn to run the application on port 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
