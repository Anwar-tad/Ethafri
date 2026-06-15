from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('marketplace', '0001_initial'),
    ]
    operations = [
        migrations.AddField(
            model_name='category',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='category',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]