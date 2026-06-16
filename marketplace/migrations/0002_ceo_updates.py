from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0001_initial'), # ከመጀመሪያው ሚግሬሽን ቀጥሎ እንዲሄድ
    ]

    operations = [
        # 1. AI የሰራቸውን ስራዎች መመዝገቢያ ሰንጠረዥ መፍጠር
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
        
        # 2. የዌብሳይቱን ዲዛይን በ AI ለመቀየር የሚያስችል ሰንጠረዥ መፍጠር
        migrations.CreateModel(
            name='SiteConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, unique=True)),
                ('value', models.JSONField(default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),

        # 3. በምርት (Product) ሞዴል ላይ የሚደረጉ ማሻሻያዎች
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

        # 4. ምርቶችን በ 7 ቋንቋዎች ለማከማቸት ሰንጠረዥ መፍጠር
        migrations.CreateModel(
            name='ProductTranslation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('en', models.TextField(blank=True, verbose_name='English')),
                ('am', models.TextField(blank=True, verbose_name='Amharic')),
                ('om', models.TextField(blank=True, verbose_name='Oromo')),
                ('ar', models.TextField(blank=True, verbose_name='Arabic')),
                ('so', models.TextField(blank=True, verbose_name='Somali')),
                ('ti', models.TextField(blank=True, verbose_name='Tigrinya')),
                ('fr', models.TextField(blank=True, verbose_name='French')),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='marketplace.product')),
            ],
        ),
    ]