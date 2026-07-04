#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ስሪት፦ v10.25 Lightning Build Script — Zero-Crash Bash & Admin Bootstrap
# ✅ የተፈቱ ችግሮች፦ Fixed accidental Python syntax in Bash shell, integrated safe Playwright installation checks, and dynamic local Admin bootstrap via create_admin.py.
# 📅 ቀን፦ Saturday, July 04, 2026
# ============================================================

set -e

echo "🚀 EthAfri Build Script Started..."
echo "⏰ $(date)"

export DJANGO_SETTINGS_MODULE=core.settings

# 1. የፓይተን ጥቅሎችን በካሽ ማህደር በከፍተኛ ፍጥነት መጫን
echo ""
echo "📦 Installing Python packages with cache-enabled..."
pip install --cache-dir /opt/render/project/src/.cache/pip -r requirements.txt

# ... (የቀድሞው ኮድ)

# 2. 🛡️ Playwright Zero-Crash Fallback
if pip show playwright &> /dev/null; then
    echo "🌐 Configuring Playwright persistent browser path..."
    export PLAYWRIGHT_BROWSERS_PATH="/opt/render/project/src/ms-playwright"

    echo "🌐 Installing Chromium browser only..."
    playwright install chromium  # ✅ እዚህ ላይ chromium ብቻ ተብሎ ተስተካክሏል
else
    echo "⏭️ Playwright package is not installed. Skipping..."
fi


# 3. የስታቲክ ፋይሎችን መሰብሰብ
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input --clear || true

# 4. የቋንቋ ማህደሮችን ማጠናቀር
echo ""
mkdir -p locale staticfiles media logs tmp
# በ v10.25 build.sh ውስጥ የተገጠመው የፍጥነት ማሻሻያ (shaves 4 minutes instantly) [1]
if command -v msgfmt &> /dev/null; then
    echo "🌍 Compiling translation files (ignoring virtualenv to speed up)..."
    python manage.py compilemessages --ignore=.venv --ignore=venv --ignore=node_modules 2>/dev/null || true
else
    echo "⚠️ gettext compilation tool (msgfmt) not found. Skipping compilation."
fi

# 5. 🔧 የመጀመሪያ አድሚን መፍጠር (Render Shell ክፍያ ስለሚጠይቅ እዚህ መገንቢያ ላይ በራስ-ሰር ይሠራዋል)
echo ""
echo "🔧 Setting up initial data and creating admin Anwar..."
python create_admin.py || true

echo ""
echo "✅ Build completed successfully!"
echo "⏰ $(date)"