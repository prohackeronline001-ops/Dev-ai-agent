# Python 3.11 ব্যবহার করুন
FROM python:3.11-slim

# Working directory তৈরি করুন
WORKDIR /app

# Environment variables সেট করুন
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# System dependencies ইনস্টল করুন
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt কপি করুন এবং ইনস্টল করুন
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot code কপি করুন
COPY bot.py .

# Bot চালান
CMD ["python", "bot.py"]
