# 🌐 1. ዋናው የድረ-ገጽ ሰርቨር (Memory-safe for Free Tier)
web: gunicorn core.wsgi:application --workers=1 --threads=1 --timeout=120

# 🤖 2. የጀርባ አውቶኖመስ CEO ኤጀንት (Parallel execution with 4 workers)
# --interval 60: በየ 60 ሰከንድ ዑደቱን ይጀምራል
# 📁 Procfile
# --concurrency 1: የ 502 ስህተትን ለመከላከል በተመሳሳይ ሰዓት 1 ስራ ብቻ እንዲሰራ
# --timeout 60: ሰርቨሩ በቶሎ ምላሽ እንዲሰጥ
worker: python manage.py run_agent --interval 120 --concurrency 1

