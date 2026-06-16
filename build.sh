#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# አድሚን እንዲፈጥር ትዕዛዝ መስጠት
python create_admin.py

# ከዚህ በፊት የነበረውን python manage.py migrate አጥፋና ይህንን ተካው
python manage.py migrate --fake marketplace 0002_auto_fix