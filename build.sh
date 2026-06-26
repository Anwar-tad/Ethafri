#!/bin/bash
# ============================================================
# 📁 ፋይል፦ EthAfri/build.sh
# 📝 ለውጥ፦ v1.4 Optimized Build Script — PostgreSQL Dual Index Safeguard (v1.4)
# ✅ የተፈቱ ችግሮች፦ relation marketplace_agent_t_ab7613_idx already exists (Postgres dual-way migration fixed!)
# 📅 ቀን፦ 2026-06-25
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
python -c "
import django
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    # ሀ. የቆዩ ሰንጠረዦች መኖራቸውን ማረጋገጥ
    cursor.execute('CREATE TABLE IF NOT EXISTS marketplace_aisystemtask (id SERIAL PRIMARY KEY);')
    cursor.execute('CREATE TABLE IF NOT EXISTS marketplace_agenttask (id SERIAL PRIMARY KEY, agent_type VARCHAR(20), status VARCHAR(20));')
    
    # ለ. ✅ FIXED: ግጭት የሚፈጥረውን አዲሱን ኢንዴክስ በ SQL አስቀድሞ ማጥፋት (already exists ስህተትን ይፈታል!) (የሕግ 3 ጥበቃ)
    cursor.execute('DROP INDEX IF EXISTS marketplace_agent_t_ab7613_idx;')
    
    # ሐ. ✅ FIXED: ጃንጎ የሚቀይረውን የድሮውን ኢንዴክስ በ SQL አስቀድሞ መፍጠር (does not exist ስህተትን ይፈታል!)
    cursor.execute('CREATE INDEX IF NOT EXISTS marketplace_agentty_847321_idx ON marketplace_agenttask (agent_type, status);')
print('✅ Legacy table and index check comp