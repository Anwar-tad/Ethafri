# ============================================================
# 📁 ፋይል፦ Procfile
# 📝 ዓላማ፦ Safe & Lightweight ASGI Procfile (v1.1)
# ✅ የተፈቱ ችግሮች፦ WebSocket connection crash prevented (Gunicorn to Uvicorn ASGI swapped), Duplicate agent thread clash resolved
# 📅 ቀን፦ 2026-06-27
# ============================================================

# ✅ FIXED: ዌብሶኬቱ እንዳይቋረጥ ኡቪኮርን (Uvicorn ASGI) ተተክሏል
# ✅ FIXED: የክሮች መጣረስን እና የክፍያ ገደብን ለመፍታት የ worker ፕሮሰስ ጠፍቷል (ኤጀንቱ በ apps.py v9.9 በጀርባ ይሠራል)
web: uvicorn core.asgi:application --host 0.0.0.0 --port $PORT --workers 1