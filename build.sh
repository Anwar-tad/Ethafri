#!/usr/bin/env bash
# EthAfri Deployment Script (optimized for Render build phase)
set -o errexit

echo "📦 Installing requirements..."
pip install -r requirements.txt

echo "🎨 Collecting static files..."
python manage.py collectstatic --no-input

echo "🚀 Build completed successfully!"