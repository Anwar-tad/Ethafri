#!/usr/bin/env bash
# EthAfri Deployment Script - Optimized for Render
set -o errexit

echo "📦 Installing requirements..."
pip install -r requirements.txt

# Start Command ላይ migrate ስላለን፣ እዚህ አያስፈልግም
echo "🎨 Collecting static files..."
python manage.py collectstatic --no-input

echo "✅ Build process finished successfully!"
