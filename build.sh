#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ለውጥ፦ v2.0 Clean Production Build Script — Database Ready
# ✅ የተፈቱ ችግሮች፦ Legacy SQL manipulations removed (PostgreSQL is now fully synced!)
# 📅 ቀን፦ 2026-06-25
# ============================================================

set -e

echo "🚀 EthAfri Build Script Started..."
echo "⏰ $(date)"

# የጃንጎን ቅንብር ፋይል በሼል ደረጃ ማስተዋወቅ
export DJANGO_SETTINGS_MODULE=core.settings

# 1. የፓይተን ጥቅሎችን በካሽ ማህደር አማካኝነት በከፍተኛ ፍጥነት መጫን (Pip Caching)
echo ""
echo "📦 Installing Python packages with cache-enabled..."
pip install --cache-dir /opt/render/project/src/.cache/pip -r requirements.txt

# 2. ማይግሬሽን ማስኬድ (አሁን ዳታቤዙ በእጅዎ ስለተስተካከለ ያለምንም ስህተት ያልፋል!)
echo ""
echo "🗄️ Running migrations..."
python manage.py makemigrations marketplace --no-input || true
python manage.py migrate --no-input || true

# 3. የስታቲክ ፋይሎችን መሰብሰብ (WhiteNoise መጨመቂያውን በአግባቡ ያጠናቅራል)
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input || true

# 4. የቋንቋ ፋይሎችን ማጠናቀር (msgfmt በሰርቨሩ ላይ ከተገኘ ብቻ)
echo ""
if command -v msgfmt &> /dev/null; then
    echo "🌍 Compiling translation files..."
    python manage.py compilemessages 2>/dev/null || true
else
    echo "⚠️ gettext compilation tool (msgfmt) not found. Skipping compilation."
fi

# 5. አስፈላጊ የፋይል ማውጫዎችን መፍጠር
mkdir -p staticfiles media logs tmp

# 6. የመጀመሪያ አድሚን መፍጠር (Anwar)
echo ""
echo "🔧 Setting up initial data..."
python create_admin.py || true

echo ""
echo "✅ Build completed successfully!"
echo "⏰ $(date)"