# ============================================================
# 📁 ፋይል፦ Procfile
# 📝 ዓላማ፦ Safe & Lightweight ASGI Procfile (v1.1 - Production Ready)
# ✅ የተፈቱ ችግሮች፦ WebSocket connection crash prevented (Gunicorn to Uvicorn ASGI swapped), Duplicate agent thread clash resolved
# 📅 ቀን፦ Monday, June 30, 2026
# ============================================================

# ✅ ዌብሶኬቱ እንዳይቋረጥ ኡቪኮርን (Uvicorn ASGI) መተግበሪያውን ያስነሳል
# ✅ የክሮች መጣረስን ለመፍታት የ worker ፕሮሰስ 1 ሆኖ ተዋቅሯል (ኤጀንቱ በ apps.py በጀርባ ይሠራል)
web: uvicorn core.asgi:application --host 0.0.0.0 --port $PORT --workers 1