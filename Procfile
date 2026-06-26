# 🌐 1. ዋናው የድረ-ገጽ ሰርቨር (Memory-safe for Free Tier)
web: gunicorn core.wsgi:application --workers=1 --threads=1 --timeout=120

# 🤖 2. የጀርባ አውቶኖመስ CEO ኤጀንት (Parallel execution with 4 workers)
# --interval 60: በየ 60 ሰከንድ ዑደቱን ይጀምራል
# --parallel 4: በአንድ ጊዜ 4 ስራዎችን በባክግራውንድ ያስኬዳል
worker: python manage.py run_agent --interval 60 --parallel 4
