#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ለውጥ፦ v10.22 Lightning Build Script — Production Persistent Browser
# ✅ የተፈቱ ችግሮች፦ Dynamic persistent Playwright browser path to prevent runtime binary loss on Render.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

set -e

echo "🚀 EthAfri Build Script Started..."
echo "⏰ $(date)"

export DJANGO_SETTINGS_MODULE=core.settings

# 1. የፓይተን ጥቅሎችን በካሽ ማህደር በከፍተኛ ፍጥነት መጫን
echo ""
echo "📦 Installing Python packages with cache-enabled..."
pip install --cache-dir /opt/render/project/src/.cache/pip -r requirements.txt

# 2. 🛡️ PERSISTENT BROWSER PATH: ብሮውዘሩ ከዲፕሎይመንት በኋላ እንዳይጠፋ በ src ውስጥ እንዲጫን ማድረግ [1]
echo "🌐 Configuring Playwright persistent browser path..."
export PLAYWRIGHT_BROWSERS_PATH="/opt/render/project/src/ms-playwright"

echo "🌐 Installing Playwright browser dependencies..."
playwright install

# 3. የስታቲክ ፋይሎችን መሰብሰብ
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input --clear || true

# 4. የቋንቋ ማህደሮችን ማጠናቀር
echo ""
mkdir -p locale staticfiles media logs tmp

if command -v msgfmt &> /dev/null; then
    echo "🌍 Compiling translation files..."
    python manage.py compilemessages 2>/dev/null || true
else
    echo "⚠️ gettext compilation tool (msgfmt) not found. Skipping compilation."
fi

# 5. የመጀመሪያ አድሚን መፍጠር
echo ""
echo "🔧 Setting up initial data..."
python create_admin.py || true

echo ""
echo "✅ Build completed successfully!"
echo "⏰ $(date)"