from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('marketplace', '0015_add_blank_to_site_registry_fields.py'), # እዚህ ጋር ካንተ የመጨረሻው ስኬታማ ማይግሬሽን ቁጥር ጋር አመሳስለው (ምናልባት 0015 ወይም 0014)
    ]

    operations = [
        # 1. Product ማሻሻያዎች
        migrations.AddField(
            model_name='product',
            name='inquiry_count',
            field=models.IntegerField(default=0, help_text='የጥያቄ ብዛት'),
        ),
        migrations.AddField(
            model_name='product',
            name='last_enhanced',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='seo_score',
            field=models.IntegerField(default=0, help_text='SEO ውጤት (0-100)'),
        ),
        migrations.AddField(
            model_name='product',
            name='view_count',
            field=models.IntegerField(default=0, help_text='የተመለከቱ ብዛት'),
        ),
        migrations.AddField(
            model_name='product',
            name='site',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='marketplace.siteregistry'),
        ),

        # 2. የትርጉም ወረፋ (TranslationQueue)
        migrations.CreateModel(
            name='TranslationQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target_languages', models.JSONField(default=list)),
                ('is_processed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pending_translations', to='marketplace.product')),
            ],
        ),

        # 3. የኤጀንት ማህደረ ትውስታ እና ስራዎች
        migrations.CreateModel(
            name='AIProjectBacklog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=255)),
                ('task_type', models.CharField(choices=[('code', 'Code Development'), ('seo', 'SEO Optimization'), ('marketing', 'Marketing Campaign'), ('acquisition', 'Customer Acquisition'), ('growth', 'Growth Strategy'), ('design', 'UI/UX Design'), ('content', 'Content Creation')], default='code', max_length=20)),
                ('target_file', models.CharField(max_length=255)),
                ('priority', models.CharField(choices=[('Critical', 'Critical'), ('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], default='Medium', max_length=20)),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('Running', 'Running'), ('Completed', 'Completed'), ('Overridden', 'Overridden'), ('Blocked', 'Blocked')], default='Pending', max_length=20)),
                ('task_hash', models.CharField(blank=True, max_length=64, unique=True)),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='backlog_tasks', to='marketplace.siteregistry')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='AgentTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent_type', models.CharField(choices=[('code', 'Code Agent'), ('seo', 'SEO Agent'), ('marketing', 'Marketing Agent'), ('data', 'Data Agent'), ('review', 'Review Agent'), ('security', 'Security Agent')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('assigned', 'Assigned'), ('running', 'Running'), ('reviewing', 'Reviewing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('task_name', models.CharField(max_length=255)),
                ('priority', models.IntegerField(default=1)),
                ('result_data', models.JSONField(blank=True, default=dict)),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agent_tasks', to='marketplace.siteregistry')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),

        # 4. ግብይት እና ደንበኞች (Marketing & SellerProfile)
        migrations.CreateModel(
            name='MarketingCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('campaign_type', models.CharField(max_length=20)),
                ('status', models.CharField(default='draft', max_length=20)),
                ('message', models.TextField()),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketing_campaigns', to='marketplace.siteregistry')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='SellerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_name', models.CharField(blank=True, max_length=255)),
                ('total_sales', models.IntegerField(default=0)),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='seller_profiles', to='marketplace.siteregistry')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='seller_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),

        # 5. የላቁ ባህሪያት (Security & AB Test)
        migrations.CreateModel(
            name='SecurityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('code_injection', 'Code Injection'), ('sql_injection', 'SQL Injection'), ('xss', 'XSS'), ('auth', 'Authentication'), ('data_leak', 'Data Leak'), ('config', 'Configuration'), ('dependency', 'Dependency')], max_length=20)),
                ('severity', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], max_length=20)),
                ('description', models.TextField()),
                ('is_fixed', models.BooleanField(default=False)),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='security_logs', to='marketplace.siteregistry')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),

        # 6. የ SiteRegistry JSONFields ማሻሻያ (blank=True)
        migrations.AlterField(
            model_name='siteregistry',
            name='competitor_urls',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='siteregistry',
            name='primary_keywords',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='siteregistry',
            name='pending_notifications',
            field=models.JSONField(blank=True, default=list),
        ),
        
        # 7. የድሮውን ቴብል ማጥፋት (Safe delete)
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS marketplace_aisystemtask CASCADE;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]