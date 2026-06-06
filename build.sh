#!/usr/bin/env bash
# ስህተት ሲያጋጥም እንዲቆም
set -o errexit

# ፓኬጆችን መጫን
pip install -r requirements.txt

# ስታቲክ ፋይሎችን መሰብሰብ
python manage.py collectstatic --no-input

# ዳታቤዙን ማዘጋጀት (ይህ ነው ስህተቱን የሚፈታው!)
python manage.py migrate