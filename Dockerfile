# Agent API image

# Base image with Python
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install kubectl
RUN apt-get update && \
    apt-get install -y curl && \
    curl -LO "https://dl.k8s.io/release/v1.27.1/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

# Install system dependencies
RUN apt-get update && apt-get install -y gcc libffi-dev

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the application port
EXPOSE 8000

# Command to run the application
CMD ["python", "agent.py"]
