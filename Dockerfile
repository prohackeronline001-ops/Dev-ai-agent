FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY chat.py .

# Run as a non-root user
RUN useradd -m appuser
USER appuser

# ✅ সিঙ্গেল ইনস্ট্যান্স নিশ্চিত করুন
CMD ["python", "chat.py"]
