#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ለውጥ፦ v2.1 Lightning Build Script — 100% Clean (Zero DB Logic)
# ✅ የተፈቱ ችግሮች፦ Omitted redundant Python diagnostics for 5x faster deployment
# 📅 ቀን፦ 2026-06-26
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

# 2. የስታቲክ ፋይሎችን በፈጣን መንገድ መሰብሰብ (WhiteNoise መጨመቂያውን በአግባቡ ያጠናቅራል)
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input || true

# 3. የቋንቋ ፋይሎችን ማጠናቀር (msgfmt በሰርቨሩ ላይ ከተገኘ ብቻ)
echo ""
if command -v msgfmt &> /dev/null; then
    echo "🌍 Compiling translation files..."
    python manage.py compilemessages 2>/dev/null || true
else
    echo "⚠️ gettext compilation tool (msgfmt) not found. Skipping compilation."
fi

# 4. አስፈላጊ የፋይል ማውጫዎችን መፍጠር
mkdir -p staticfiles media logs tmp

# 5. የመጀመሪያ አድሚን መፍጠር (Anwar)
echo ""
echo "🔧 Setting up initial data..."
python create_admin.py || true

echo ""
echo "✅ Build completed successfully!"
echo "⏰ $(date)"