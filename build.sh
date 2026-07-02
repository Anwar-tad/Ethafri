#!/bin/bash
set -e

echo "🚀 Starting Build Process..."

# 1. መጀመሪያ ፓኬጆችን መጫን (ይህ መስመር የጎደለህ ነው!)
echo "📦 Installing Requirements..."
pip install -r requirements.txt

# 2. Playwright መጫን
echo "🌐 Installing Playwright..."
playwright install chromium

# 3. Django commands
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input

echo "✅ Build completed successfully!"
