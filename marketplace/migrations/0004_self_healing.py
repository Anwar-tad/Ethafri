# EthAfri/marketplace/migrations/0004_self_healing.py

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0003_ceo_updates'), # ከቀድሞው የ CEO ማሻሻያ ሚግሬሽን ቀጥሎ እንዲሄድ
    ]

    operations = [
        # የ AI ራስ-አራሚ ታሪክ መመዝገቢያ ሰንጠረዥ በዳታቤዝ ውስጥ መፍጠር
        migrations.CreateModel(
            name='SelfHealingLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('error_message', models.TextField()),
                ('solution_sql', models.TextField(blank=True, null=True)),
                ('resolved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]