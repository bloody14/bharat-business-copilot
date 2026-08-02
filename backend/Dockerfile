FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Copy project configuration and all source files required for packaging and migrations
COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY start.sh ./

# Make start.sh executable
RUN chmod +x start.sh

# Install the package and its dependencies
RUN pip install --no-cache-dir .

EXPOSE 8000

# Use the startup script to run migrations then boot the server
CMD ["./start.sh"]
