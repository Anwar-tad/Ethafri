# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/migrations/0017_universal_marketplace.py
# 📝 ዓላማ፦ Universal Marketplace Database Schema Migration (Phase 1)
# ✅ የተፈቱ ችግሮች፦ Dynamic category types, multiple images, and direct WhatsApp/Imo seller contact fields
# 📅 ቀን፦ Monday, June 29, 2026
# ============================================================

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        # 🟢 ከላኩልኝ የ 0016 የማይግሬሽን ፋይል ጋር በደህንነት ይተሳሰራል
        ('marketplace', '0016_product_indexing'),
    ]

    operations = [
        # 1. ⚡ የካቴጎሪ ዘርፍ መለያ መስክ (category_type) በ Category ሞዴል ላይ መጫን
        migrations.AddField(
            model_name='category',
            name='category_type',
            field=models.CharField(
                choices=[
                    ('goods', 'አጠቃላይ ዕቃዎች (Goods)'),
                    ('property', 'ቤቶችና ኪራይ (Property & Rent)'),
                    ('vehicle', 'መኪናዎችና ትራንስፖርት (Vehicles)'),
                    ('service', 'ሙያዊ አገልግሎቶች (Services)'),
                    ('job', 'የሥራ ማስታወቂያዎች (Jobs)'),
                ],
                default='goods',
                help_text='ይህ ካቴጎሪ የሚመደብበትን ዋና የገበያ ዘርፍ ይምረጡ',
                max_length=20
            ),
        ),
        # 2. ⚡ የኪራይ/የሽያጭ መለያ መስክ (listing_type) በ Product ሞዴል ላይ መጫን
        migrations.AddField(
            model_name='product',
            name='listing_type',
            field=models.CharField(
                choices=[
                    ('sale', 'ለሽያጭ (For Sale)'),
                    ('rent', 'ለኪራይ (For Rent)'),
                    ('service', 'አገልግሎት / ስራ (Service)'),
                ],
                default='sale',
                help_text='የምርቱን ሽያጭ ወይም ኪራይ ሁኔታ ይምረጡ',
                max_length=20
            ),
        ),
        # 3. ⚡ የባለቤቱ ስልክ/አድራሻ መስክ (contact_info) በ Product ሞዴል ላይ መጫን
        migrations.AddField(
            model_name='product',
            name='contact_info',
            field=models.CharField(
                blank=True,
                default='',
                help_text='የባለቤቱ ስልክ ወይም ዩዘርኔም',
                max_length=255
            ),
        ),
        # 4. ⚡ የበርካታ ምስሎች ስብስብ መስክ (image_gallery) በ Product ሞዴል ላይ መጫን
        migrations.AddField(
            model_name='product',
            name='image_gallery',
            field=models.TextField(
                blank=True,
                default='[]',
                help_text='የምስሎች ስብስብ ዝርዝር (JSON Array)'
            ),
        ),
    ]