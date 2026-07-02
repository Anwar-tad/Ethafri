#!/bin/bash
set -e
# Nixpacks ሁሉንም ነገር ይጭንልናል፣ እኛ የምንፈልገው መሮጥ ብቻ ነው
python manage.py collectstatic --no-input
python manage.py migrate
python create_admin.py || true
