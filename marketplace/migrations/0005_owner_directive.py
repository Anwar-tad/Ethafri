# EthAfri/marketplace/migrations/0005_owner_directive.py

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0004_self_healing'), # ከቀደመው የራስ-አራሚ ሞዴል ሚግሬሽን ቀጥሎ እንዲሄድ
    ]

    operations = [
        # የባለቤት መመሪያ (Owner Directive) ሰንጠረዥ በዳታቤዝ ውስጥ መፍጠር
        migrations.CreateModel(
            name='OwnerDirective',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instruction', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]