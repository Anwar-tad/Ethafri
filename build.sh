#!/bin/bash
set -e

echo "🚀 EthAfri Build Script Started..."
export DJANGO_SETTINGS_MODULE=core.settings

# 1. ፓኬጆችን መጫን
echo "📦 Installing Python packages..."
pip install --cache-dir /opt/render/project/src/.cache/pip -r requirements.txt

# 2. 🛡️ PLAYWRIGHT BROWSER & DEPENDENCIES (ይህ ክፍል ወሳኝ ነው!)
echo "🌐 Configuring and installing Playwright dependencies..."
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright

# Chromium-ን እና አስፈላጊ የሆኑትን የOS Libraries መጫን
python -m playwright install chromium


# የብሮውዘር ማህደርን ለሰርቨሩ ክፍት ማድረግ
chmod -R 777 /opt/render/.cache/ms-playwright

# 3. የስታቲክ ፋይሎች
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input --clear || true

# 4. ማውጫዎችን መፍጠር
mkdir -p locale staticfiles media logs tmp

# 5. የቋንቋ ማጠናቀር
if command -v msgfmt &> /dev/null; then
    python manage.py compilemessages 2>/dev/null || true
fi

# 6. አድሚን
python create_admin.py || true

echo "✅ Build completed successfully!"
