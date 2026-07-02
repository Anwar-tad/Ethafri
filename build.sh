#!/bin/bash
set -e

echo "📦 Installing Dependencies & Running Build..."

# 1. ፓኬጆችን በ requirements.txt መሰረት መጫን
pip install -r requirements.txt

# 2. Playwright Chromium ን መጫን (nixpacks ካልጫነው ብሎ)
python -m playwright install chromium

# 3. የስታቲክ ፋይሎችን መሰብሰብ (ስህተት ቢኖርም አያቁም)
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input || echo "⚠️ Static collection failed, but continuing..."

# 4. ዳታቤዝ ማይግሬሽን
echo "🔧 Running migrations..."
python manage.py makemigrations
python manage.py migrate --no-input

echo "✅ Build Process Finished Successfully!"
