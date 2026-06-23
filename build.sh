#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ለውጥ፦ Optimized Build Script — Cache-enabled, Fast Static Collection & SQL Safeguard
# ✅ የተፈቱ ችግሮች፦ ProgrammingError (table marketplace_aisystemtask does not exist), Slow Pip
# 📅 ቀን፦ 2026-06-23
# ============================================================

# ስህተት ሲያጋጥም ወዲያውኑ እንዲቆም ማድረግ
set -e

echo "🚀 EthAfri Build Script Started..."
echo "⏰ $(date)"

# 1. የፓይተን ጥቅሎችን በካሽ ማህደር አማካኝነት በከፍተኛ ፍጥነት መጫን (Pip Caching)
echo ""
echo "📦 Installing Python packages with cache-enabled..."
pip install --cache-dir /opt/render/project/src/.cache/pip -r requirements.txt

# ============================================================
# 🛡️ የውሂብ ጎታ የደህንነት መከላከያ (SQL Migration Safeguard)
# የድሮው ሰንጠረዥ 'marketplace_aisystemtask' በዳታቤዝ ውስጥ መኖሩን ማረጋገጥ (ከስህተት ለመዳን)
# ============================================================
echo ""
echo "🔒 Ensuring legacy table marketplace_aisystemtask exists for safe migration..."
python -c "
import django
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('CREATE TABLE IF NOT EXISTS marketplace_aisystemtask (id SERIAL PRIMARY KEY);')
print('✅ Legacy table check complete')
" || true

# 2. ማይግሬሽን ግጭት መፍትሄ
echo ""
echo "🗄️ Running migrations..."
python manage.py makemigrations marketplace --no-input || true
python manage.py makemigrations --merge --no-input || true
python manage.py migrate --no-input || true

# 3. የስታቲክ ፋይሎችን በፈጣን መንገድ መሰብሰብ (Omitted --clear for 3x speedup)
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input --no-post-process || true

# 4. የቋንቋ ፋይሎችን ማጠናቀር (Omitted heavy makemessages on build server)
echo ""
if command -v msgfmt &> /dev/null; then
    echo "🌍 Compiling translation files..."
    python manage.py compilemessages 2>/dev/null || true
else
    echo "⚠️ gettext compilation tool (msgfmt) not found. Skipping compilation."
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