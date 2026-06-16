# EthAfri/marketplace/migrations/0003_ceo_updates.py
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0002_auto_fix'), # ከቀድሞው ስህተት ማስተካከያ ቀጥሎ እንዲሄድ
    ]

    operations = [
        migrations.CreateModel(
            name='AISystemTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=255)),
                ('priority_reason', models.TextField()),
                ('status', models.CharField(default='Completed', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='SiteConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, unique=True)),
                ('value', models.JSONField(default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='image_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='products/'),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.CreateModel(
            name='ProductTranslation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='marketplace.product')),
                ('en', models.TextField(blank=True, verbose_name='English')),
                ('am', models.TextField(blank=True, verbose_name='Amharic')),
                ('om', models.TextField(blank=True, verbose_name='Oromo')),
                ('ar', models.TextField(blank=True, verbose_name='Arabic')),
                ('so', models.TextField(blank=True, verbose_name='Somali')),
                ('ti', models.TextField(blank=True, verbose_name='Tigrinya')),
                ('fr', models.TextField(blank=True, verbose_name='French')),
            ],
        ),
    ]