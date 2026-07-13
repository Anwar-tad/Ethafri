#!/usr/bin/env bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ስሪት፦ v10.26 Lightning Build Script — Zero-Crash Bash & Admin Bootstrap
# ✅ የተፈቱ ችግሮች፦ Integrated missing 'python manage.py migrate --no-input' command to prevent unmigrated database crashes, configured persistent Playwright browser cache path, and automated create_admin.py bootstrapping.
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

set -e

echo "🚀 EthAfri Build Script Started..."
echo "⏰ $(date)"

export DJANGO_SETTINGS_MODULE=core.settings

# 1. የፓይተን ጥቅሎችን በካሽ ማህደር በከፍተኛ ፍጥነት መጫን
echo ""
echo "📦 Installing Python packages with cache-enabled..."
pip install --cache-dir /opt/render/project/src/.cache/pip -r requirements.txt

# 2. 🌐 Playwright Zero-Crash Fallback
if pip show playwright &> /dev/null; then
    echo "🌐 Configuring Playwright persistent browser path..."
    export PLAYWRIGHT_BROWSERS_PATH="/opt/render/project/src/ms-playwright"

    echo "🌐 Installing Chromium browser only..."
    playwright install chromium
else
    echo "⏭️ Playwright package is not installed. Skipping..."
fi

# 🛡️ 3. 🌱 የዳታቤዝ ሰንጠረዦችን ማሻሻል (Database Migrations)
# FIXED: Added migration command to prevent empty database crashes on start
echo ""
echo "🌱 Running database migrations..."
python manage.py migrate --no-input

# 4. የስታቲክ ፋይሎችን መሰብሰብ
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input --clear || true

# 5. የቋንቋ ማህደሮችን ማጠናቀር
echo ""
mkdir -p locale staticfiles media logs tmp

if command -v msgfmt &> /dev/null; then
    echo "🌍 Compiling translation files (ignoring virtualenv to speed up)..."
    python manage.py compilemessages --ignore=.venv --ignore=venv --ignore=node_modules 2>/dev/null || true
else
    echo "⚠️ gettext compilation tool (msgfmt) not found. Skipping compilation."
fi

# 6. 🔧 የመጀመሪያ አድሚን መፍጠር
echo ""
echo "🔧 Setting up initial data and creating admin Anwar..."
python create_admin.py || true

echo ""
echo "✅ Build completed successfully!"
echo "⏰ $(date)"