FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir .
CMD ["marketplace-api"]

