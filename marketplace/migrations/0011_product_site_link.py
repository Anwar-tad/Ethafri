# EthAfri/marketplace/migrations/0011_product_site_link.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        # ⚠️ ወደ ትክክለኛው የፋይልህ ስም '0010_site_registry_and_orchestration' ተስተካክሏል! [1]
        ('marketplace', '0010_site_registry_and_orchestration'), 
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
    


