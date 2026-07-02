# ============================================================
# 📁 ፋይል፦ Procfile
# 📝 ዓላማ፦ Safe & Lightweight ASGI Procfile (v10.16 - Production Ready)
# ✅ የተፈቱ ችግሮች፦ Dynamic proxy headers enabled, WebSocket connection crash prevented, and duplicate agent threads locked.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

# ✅ ዌብሶኬቱ እንዳይቋረጥ ኡቪኮርን (Uvicorn ASGI) መተግበሪያውን ያስነሳል
# ✅ የክሮች መጣረስን ለመፍታት የ worker ፕሮሰስ 1 ሆኖ ተዋቅሯል (ኤጀንቱ በ apps.py በጀርባ ይሠራል)
# ✅ --forwarded-allow-ips='*' ሬንደር በሚጠቀምበት የሪቨርስ ፕሮክሲ (Reverse Proxy) መረብ ላይ ግንኙነቶች እንዳይቋረጡ ያረጋግጣል [1]
web: uvicorn core.asgi:application --host 0.0.0.0 --port $PORT --workers 1 --forwarded-allow-ips='*'