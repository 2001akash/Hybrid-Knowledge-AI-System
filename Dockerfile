FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN apt-get update && apt-get install -y build-essential libgl1-mesa-glx && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]