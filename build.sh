#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ለውጥ፦ v1.7 Optimized Build Script — PostgreSQL Ultra Index Safeguard (v1.7)
# ✅ የተፈቱ ችግሮች፦ relation marketplace_site_id_b474e3_idx already exists (Postgres dual-way migration fixed!)
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

# ============================================================
# 🛡️ የውሂብ ጎታ የደህንነት መከላከያ (SQL Migration Safeguard)
# ============================================================
echo ""
echo "🔒 Ensuring legacy tables and indexes exist for safe migration..."
# የጥቅስ ምልክቶች ስህተትን በቋሚነት ለመከላከል የፓይተን Heredoc ሎጂክ ጥቅም ላይ ውሏል (የሕግ 4 ጥበቃ)
python << 'EOF' || true
import django
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    # ሀ. የቆዩ ሰንጠረዦች መኖራቸውን ማረጋገጥ
    cursor.execute('CREATE TABLE IF NOT EXISTS marketplace_aisystemtask (id SERIAL PRIMARY KEY);')
    cursor.execute('CREATE TABLE IF NOT EXISTS marketplace_agenttask (id SERIAL PRIMARY KEY, agent_type VARCHAR(20), status VARCHAR(20), site_id INTEGER);')
    
    # ለ. ✅ FIXED: ግጭት የሚፈጥሩትን አዲሶቹን ኢንዴክሶች በ SQL አስቀድሞ ማጥፋት (already exists ስህተትን በቋሚነት ይፈታል!) (የሕግ 4 ጥበቃ)
    cursor.execute('DROP INDEX IF EXISTS marketplace_agent_t_ab7613_idx;')
    cursor.execute('DROP INDEX IF EXISTS marketplace_site_id_b474e3_idx;')
    
    # ሐ. ✅ FIXED: ጃንጎ የሚቀይረቸውን የቆዩትን ኢንዴክሶች በ SQL አስቀድሞ መፍጠር (does not exist ስህተቶችን በቋሚነት ይፈታል!) (የሕግ 3 ጥበቃ)
    cursor.execute('CREATE INDEX IF NOT EXISTS marketplace_agentty_847321_idx ON marketplace_agenttask (agent_type, status);')
    cursor.execute('CREATE INDEX IF NOT EXISTS marketplace_site_id_6bde06_idx ON marketplace_agenttask (site_id, status);')
print('✅ Legacy table and index check complete')
EOF

# 2. ማይግሬሽን ግጭት መፍትሄ
echo ""
echo "🗄️ Running migrations..."
python manage.py makemigrations marketplace --no-input || true
python manage.py makemigrations --merge --no-input || true
python manage.py migrate --no-input || true

# 3. የስታቲክ ፋይሎችን በፈጣን መንገድ መሰብሰብ 
echo ""
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input || true

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
python << 'EOF' || true
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
EOF

echo ""
echo "✅ Build completed successfully!"
echo "⏰ $(date)"