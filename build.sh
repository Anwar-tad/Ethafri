#!/bin/bash

# ማንኛውም ስህተት ሲያጋጥም ስክሪፕቱ እንዲቆም ያደርጋል
set -e

echo "🚀 Starting Optimized Build Process for EthAfri..."
echo "⏰ Time: $(date)"

# 1. ጥቅሎችን መጫን (Pip Caching በመጠቀም ፍጥነቱን ይጨምራል)
echo "📦 Installing dependencies..."
pip install --cache-dir /opt/render/project/src/.cache/pip -r requirements.txt

# 2. የዳታቤዝ ማይግሬሽን (ቀድሞ ስላስተካከልከው አሁን በቀጥታ ይሰራል)
echo "🗄️ Applying database migrations..."
python manage.py migrate --no-input

# 3. የስታቲክ ፋይሎችን መሰብሰብ (ለ CSS/JS/Images)
echo "📂 Collecting static files..."
python manage.py collectstatic --no-input

# 4. የቋንቋ ፋይሎችን ማጠናቀር (ለአማርኛ፣ ኦሮምኛ እና ሌሎች ትርጉሞች)
if command -v msgfmt &> /dev/null; then
    echo "🌍 Compiling translation messages..."
    python manage.py compilemessages
else
    echo "⚠️ Warning: gettext not found, skipping translation compilation."
fi

# 5. አስፈላጊ የሆኑ ማውጫዎችን (Directories) መፍጠር
echo "📁 Ensuring required directories exist..."
mkdir -p staticfiles
mkdir -p media
mkdir -p logs

# 6. የመጀመሪያ መረጃዎችን ማዘጋጀት (Admin/SiteRegistry)
echo "🔧 Running initial setup scripts..."
if [ -f "create_admin.py" ]; then
    python create_admin.py || echo "⚠️ Admin setup script failed or already ran."
fi

# 7. የሲስተም ጤንነት ፍተሻ (Health Check)
echo "🔍 Verifying system status..."
python -c "
import django
django.setup()
from django.db import connection
from marketplace.models import SiteRegistry

try:
    connection.ensure_connection()
    site_count = SiteRegistry.objects.count()
    print(f'✅ Database Connected. Registered Sites: {site_count}')
except Exception as e:
    print(f'❌ System check failed: {e}')
    exit(1)
"

echo "✅ Build Process Completed Successfully!"
echo "⏰ End Time: $(date)"