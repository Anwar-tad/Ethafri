from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [('marketplace', '0004_self_healing')]
    operations = [
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