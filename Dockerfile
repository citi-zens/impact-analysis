FROM golang:1.24 AS builder

RUN go install github.com/mark3labs/mcphost@latest

# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the entrypoint
# COPY docker/entrypoint.sh /app/docker/entrypoint.sh
# RUN chmod +x /app/docker/entrypoint.sh

# Install Git (and dependencies)
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /go/bin/mcphost /usr/local/bin/mcphost

RUN chmod +x /usr/local/bin/mcphost

RUN mcphost --help || true

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8090

# Command to run the application
# --host 0.0.0.0 is crucial for Docker networking
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]