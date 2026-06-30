# Use a lightweight, official Python runtime
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Run your main script when the container starts
CMD ["python", "main.py"]