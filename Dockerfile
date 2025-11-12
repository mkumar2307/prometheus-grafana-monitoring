# Dockerfile
FROM python:3.11-slim

# Create a non-root user
ENV APP_USER=appuser
ENV APP_HOME=/home/${APP_USER}/app
RUN groupadd -r ${APP_USER} && useradd -r -g ${APP_USER} -d ${APP_HOME} -s /sbin/nologin ${APP_USER}

WORKDIR ${APP_HOME}

# Install system deps needed for uvicorn or common libs (keep minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . ${APP_HOME}

# Ensure correct ownership
RUN chown -R ${APP_USER}:${APP_USER} ${APP_HOME}

# Switch to non-root user for running the app
USER ${APP_USER}

EXPOSE 8000

# Use Uvicorn with multiple workers for production; graceful shutdown settings can be tuned.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]