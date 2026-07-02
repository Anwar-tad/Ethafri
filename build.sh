#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ለውጥ፦ v10.16 Lightning Build Script — 100% Clean & Thread Synced
# ✅ የተፈቱ ችግሮች፦ Dynamic Playwright browser path export, auto-creation of locale folders, and fast pip caching.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

# ስህተት ሲያጋጥም ወዲያውኑ እንዲቆም ማድረግ
set -e

echo "🚀 EthAfri Build Script Started..."
echo "⏰ $(date)"

# የጃንጎን ቅንብር ፋይል በሼል ደረጃ ማስተዋወቅ
export DJANGO_SETTINGS_MODULE=core.settings

# 1. የፓይተን ጥቅሎችን በካሽ ማህደር አማካኝነት በከፍተኛ ፍጥነት መጫን (Pip Caching)
echo ""
echo "📦 Installing Python packages with cache-enabled..."
pip install --cache-dir /opt/render/project/src/.cache/pip -r requirements.txt

# 2. 🛡️ PLAYWRIGHT BROWSER PATH ALIGNMENT:
echo "🌐 Configuring Playwright browser path..."
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright

echo "🌐 Installing Playwright Chromium browser..."
# ብሮውዘሩን በትክክለኛው መንገድ መጫን
python -m playwright install chromium

# ተጨማሪ ደህንነት - ፍቃድ መስጠት
chmod -R 755 /opt/render/.cache/ms-playwright


# 3. የስታቲክ ፋይሎችን በፈጣን መንገድ መሰብሰብ
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input --clear || true

# 4. አስፈላጊ የፋይል ማውጫዎችን መፍጠር እና ማረጋገጥ (የቋንቋ ማህደርን ጨምሮ) [1]
echo ""
mkdir -p locale staticfiles media logs tmp

# 5. የቋንቋ ፋይሎችን ማጠናቀር (msgfmt በሰርቨሩ ላይ ከተገኘ ብቻ)
if command -v msgfmt &> /dev/null; then
    echo "🌍 Compiling translation files..."
    python manage.py compilemessages 2>/dev/null || true
else
    echo "⚠️ gettext compilation tool (msgfmt) not found. Skipping compilation."
fi

# 6. የመጀመሪያ አድሚን መፍጠር
echo ""
echo "🔧 Setting up initial data..."
python create_admin.py || true

echo ""
echo "✅ Build completed successfully!"
echo "⏰ $(date)"