# ============================================================
# 📁 ፋይል፦ EthAfri/Procfile
# 📝 ለውጥ፦ v1.1 Production Procfile — Dynamic Interval & Concurrency Safe
# ✅ የተፈቱ ችግሮች፦ Dynamic AGENT_INTERVAL Mapping on Worker process (Free Tier Friendly)
# 📅 ቀን፦ 2026-06-25
# ============================================================

# 🌐 1. ዋናው የድረ-ገጽ ሰርቨር (gunicorn memory-safe threads)
web: gunicorn core.wsgi:application --workers=1 --threads=1 --timeout=120

# 🤖 2. የጀርባ አውቶኖመስ CEO ኤጀንት (በዳሽቦርዱ የጊዜ መኝታ ገደብ መሠረት ይነሳል)
worker: python manage.py run_agent --interval $AGENT_INTERVAL