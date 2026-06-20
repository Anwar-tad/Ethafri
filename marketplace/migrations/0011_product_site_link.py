# EthAfri/marketplace/migrations/0011_product_site_link.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        # ⚠️ ከዚህ በፊት የተገነባው ማይግሬሽንህ '0010_site_orchestration' መሆኑን አረጋግጥ
        ('marketplace', '0010_site_orchestration'), 
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='site',
            field=models.ForeignKey(
                blank=True, 
                help_text='ይህ ምርት የሚለጠፍበትን ጣቢያ ይምረጡ', 
                null=True, 
                on_delete=django.db.models.deletion.CASCADE, 
                related_name='products', 
                to='marketplace.siteregistry'
            ),
        ),
    ]