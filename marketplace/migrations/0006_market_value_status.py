# EthAfri/marketplace/migrations/0006_market_value_status.py

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        # ⚠️ ከቀድሞው የባለቤት መመሪያ ሚግሬሽን (0005) ቀጥሎ እንዲሄድ
        ('marketplace', '0005_owner_directive'), 
    ]

    operations = [
        # በ Product ሞዴል ላይ market_value_status መኖሩን ለዲጃንጎ ማሳወቅ
        migrations.AddField(
            model_name='product',
            name='market_value_status',
            field=models.CharField(blank=True, default='Unknown', max_length=50),
        ),
    ]