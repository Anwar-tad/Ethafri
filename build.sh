#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ለውጥ፦ የተሻሻለ — Render Free Tier Optimized
# 📅 ቀን፦ 2026-06-20
# ============================================================

set -e  # ስህተት ካለ ግንባታውን ያቁም

echo "🚀 EthAfri Build Script Started..."

# 1. የፓይተን ጥቅሎችን መጫን
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. ስታቲክ ፋይሎችን መሰብሰብ
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input

# 3. የቋንቋ ፋይሎችን ማጠናቀር
echo "🌍 Compiling translation files..."
if command -v xgettext &> /dev/null; then
    python manage.py makemessages --locale=am --locale=om --locale=ar --locale=so --locale=ti --locale=fr --ignore=.venv/* --ignore=node_modules/* 2>/dev/null || true
    python manage.py compilemessages 2>/dev/null || true
else
    echo "⚠️ gettext not found. Skipping translation compilation."
fi

echo "✅ Build completed successfully!"