FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EGM_HOST=0.0.0.0 \
    EGM_SECURE_COOKIES=1

WORKDIR /app

COPY fullstack/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY fullstack/ ./

EXPOSE 8040

CMD ["python", "server.py"]
