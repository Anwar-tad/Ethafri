# የፓይተን ስሪት
FROM python:3.11-slim

# ለPlaywright የሚሆኑ የOS ዲፔንደንሲዎችን መጫን
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm-dev \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# ፓኬጆችን መጫን
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# አፕሊኬሽኑን ማስጀመር (ለምሳሌ uvicorn)
CMD ["uvicorn", "core.asgi:application", "--host", "0.0.0.0", "--port", "10000"]
