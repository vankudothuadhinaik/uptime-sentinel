FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY proxy.py /app/proxy.py
RUN useradd --create-home --uid 10001 proxyuser
USER proxyuser
EXPOSE 8080
CMD ["python", "/app/proxy.py"]
