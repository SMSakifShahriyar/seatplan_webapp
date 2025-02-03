# Use an official Python 3.9 slim image as the base
FROM python:3.9-slim

# Set environment variables to improve Python performance
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application code to the working directory
COPY . .

# Expose the port that your app will run on
EXPOSE 8000

# Install Gunicorn for production serving
RUN pip install gunicorn

# Use Gunicorn to run your Flask application (adjust the port if needed)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
