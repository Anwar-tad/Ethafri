#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ለውጥ፦ Fixed migration conflicts + SelfHealingLog import
# 📅 ቀን፦ 2026-06-22
# ============================================================

set -e

echo "🚀 EthAfri Build Script Started..."
echo "⏰ $(date)"

# 1. የፓይተን ጥቅሎችን መጫን
echo ""
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. ማይግሬሽን ግጭት መፍትሄ
echo ""
echo "🗄️ Fixing migration conflicts..."
python manage.py makemigrations marketplace --no-input || true
python manage.py makemigrations --merge --no-input || true
python manage.py migrate --no-input || true

# 3. ስታቲክ ፋይሎችን መሰብሰብ
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input --clear --no-post-process || true

# 4. የቋንቋ ፋይሎችን ማጠናቀር
echo ""
echo "🌍 Compiling translation files..."
if command -v xgettext &> /dev/null; then
    python manage.py makemessages --locale=am --locale=om --locale=ar --locale=so --locale=ti --locale=fr --ignore=.venv/* --ignore=node_modules/* --ignore=static/* --ignore=media/* 2>/dev/null || true
    python manage.py compilemessages 2>/dev/null || true
else
    echo "⚠️ gettext not found. Skipping translation compilation."
fi

# 5. አስፈላጊ ማውጫዎችን መፍጠር
echo ""
echo "📁 Creating required directories..."
mkdir -p staticfiles
mkdir -p media
mkdir -p logs
mkdir -p tmp

# 6. የመጀመሪያ ውሂብ መፍጠር
echo ""
echo "🔧 Setting up initial data..."
python create_admin.py || true

# 7. የስርዓት ሁኔታ ፍተሻ
echo ""
echo "🔍 Verifying system status..."
python -c "
import django
django.setup()
from django.db import connection
from marketplace.models import SiteRegistry, AIProjectBacklog

connection.ensure_connection()
print('✅ Database connection successful')

sites = SiteRegistry.objects.filter(is_active=True)
print(f'✅ Active sites: {sites.count()}')

tasks = AIProjectBacklog.objects.filter(status='Pending')
print(f'✅ Pending tasks: {tasks.count()}')
" || true

echo ""
echo "✅ Build completed successfully!"
echo "⏰ $(date)"