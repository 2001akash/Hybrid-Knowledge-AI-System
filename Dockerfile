FROM python:3.10-slim

WORKDIR /app
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install dependencies
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "app.py"]
