# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/migrations/0016_product_indexing.py
# 📝 ዓላማ፦ Database Indexing Migration — High-Performance Speedups (v1.0)
# ✅ የተፈቱ ችግሮች፦ Database full-table scan on Home Page, views.py query latency
# 📅 ቀን፦ Friday, June 26, 2026
# ============================================================

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        # ✅ ከላኩልኝ የ 0015 ማይግሬሽን ጋር በደህንነት ይተሳሰራል (የሕግ 3 ጥበቃ)
        ('marketplace', '0015_add_blank_to_site_registry_fields'),
    ]

    operations = [
        # 1. ⚡ በምርት ሁኔታ (is_active) ላይ ኢንዴክስ መጫን (የፍለጋ ፍጥነትን ለማሳደግ)
        migrations.AlterField(
            model_name='product',
            name='is_active',
            field=models.BooleanField(db_index=True, default=True),
        ),
        # 2. ⚡ በምርት መፈጠሪያ ጊዜ (created_at) ላይ ኢንዴክስ መጫን (የመደርደርያ ፍጥነትን ለማሳደግ)
        migrations.AlterField(
            model_name='product',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]