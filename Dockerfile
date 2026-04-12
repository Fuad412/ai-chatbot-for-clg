# Use the official lightweight Python image
# https://hub.docker.com/_/python
FROM python:3.10-slim

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code specifically
COPY . .

# Expose port (Cloud Run uses PORT environment variable, defaults to 8080)
ENV PORT 8080
EXPOSE 8080

# Run the web service on container startup using gunicorn
# 1 worker and 8 threads are a good starting point for Cloud Run
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
