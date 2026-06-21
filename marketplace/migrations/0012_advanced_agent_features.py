# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/migrations/0002_advanced_agent_features.py
# 📝 ለውጥ፦ Advanced Agent Features (VectorMemory, AgentTask, ABTest, SecurityLog, PredictionLog, ExternalAPI)
# 📅 ቀን፦ 2026-06-22
# ============================================================

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0001_initial'),
    ]

    operations = [
        # ============================================================
        # 1. VectorMemory Model
        # ============================================================
        migrations.CreateModel(
            name='VectorMemory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('memory_type', models.CharField(choices=[('error', 'Error Resolution'), ('solution', 'Solution Pattern'), ('code', 'Code Snippet'), ('insight', 'Market Insight'), ('strategy', 'Strategy Pattern')], max_length=20)),
                ('content', models.TextField(help_text='የትውስታ ይዘት')),
                ('embedding', models.JSONField(blank=True, default=list, help_text='pgvector embedding (future use)')),
                ('metadata', models.JSONField(default=dict, help_text='ተጨማሪ መረጃ (site, task, success_rate)')),
                ('usage_count', models.IntegerField(default=0, help_text='ምን ያህል ጊዜ ጥቅም ላይ ውሏል')),
                ('success_rate', models.FloatField(default=0.0, help_text='ስኬታማነት መጠን 0-100')),
                ('last_used', models.DateTimeField(blank=True, null=True)),
                ('text_content', models.TextField(blank=True, help_text='The original text content that was vectorized.')),
                ('vector_data', models.JSONField(default=dict, help_text='JSON representation of the vector embedding.')),
                ('embedding_model', models.CharField(default='default-embedding-model', help_text='The name or identifier of the embedding model used to generate this vector.', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(blank=True, help_text='The product this vector memory is associated with.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vector_memories', to='marketplace.product')),
                ('related_task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='memory_entries', to='marketplace.aiprojectbacklog')),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='memory_entries', to='marketplace.siteregistry')),
            ],
            options={
                'ordering': ['-success_rate', '-usage_count'],
            },
        ),
        migrations.AddIndex(
            model_name='vectormemory',
            index=models.Index(fields=['memory_type', 'site'], name='marketplace_memory_78b3bd_idx'),
        ),
        migrations.AddIndex(
            model_name='vectormemory',
            index=models.Index(fields=['-created_at'], name='marketplace_created_4e9187_idx'),
        ),
        migrations.AddIndex(
            model_name='vectormemory',
            index=models.Index(fields=['product'], name='marketplace_product_771a46_idx'),
        ),
        migrations.AddIndex(
            model_name='vectormemory',
            index=models.Index(fields=['embedding_model'], name='marketplace_embeddi_3bb1ff_idx'),
        ),
        
        # ============================================================
        # 2. AgentTask Model
        # ============================================================
        migrations.CreateModel(
            name='AgentTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent_type', models.CharField(choices=[('code', 'Code Agent'), ('seo', 'SEO Agent'), ('marketing', 'Marketing Agent'), ('data', 'Data Agent'), ('review', 'Review Agent'), ('security', 'Security Agent')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('assigned', 'Assigned'), ('running', 'Running'), ('reviewing', 'Reviewing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('task_name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('priority', models.IntegerField(default=1, help_text='1-10 (10 ከፍተኛ)')),
                ('result_data', models.JSONField(blank=True, default=dict)),
                ('error_message', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional task metadata')),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('backlog_task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='agent_tasks', to='marketplace.aiprojectbacklog')),
                ('parent_task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subtasks', to='marketplace.agenttask')),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agent_tasks', to='marketplace.siteregistry')),
            ],
            options={
                'ordering': ['-priority', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='agenttask',
            index=models.Index(fields=['agent_type', 'status'], name='marketplace_agent_1cfc13_idx'),
        ),
        migrations.AddIndex(
            model_name='agenttask',
            index=models.Index(fields=['site', 'status'], name='marketplace_site_id_97bae9_idx'),
        ),
        
        # ============================================================
        # 3. ABTest Model
        # ============================================================
        migrations.CreateModel(
            name='ABTest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('running', 'Running'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('variant_a', models.JSONField(help_text='የመጀመሪያ ስሪት')),
                ('variant_b', models.JSONField(help_text='ሁለተኛ ስሪት')),
                ('winner', models.CharField(blank=True, max_length=10)),
                ('variant_a_views', models.IntegerField(default=0)),
                ('variant_b_views', models.IntegerField(default=0)),
                ('variant_a_conversions', models.IntegerField(default=0)),
                ('variant_b_conversions', models.IntegerField(default=0)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ab_tests', to='marketplace.siteregistry')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        # ============================================================
        # 4. SecurityLog Model
        # ============================================================
        migrations.CreateModel(
            name='SecurityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('code_injection', 'Code Injection'), ('sql_injection', 'SQL Injection'), ('xss', 'XSS'), ('auth', 'Authentication'), ('data_leak', 'Data Leak'), ('config', 'Configuration'), ('dependency', 'Dependency')], max_length=20)),
                ('severity', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], max_length=20)),
                ('description', models.TextField()),
                ('file_path', models.CharField(blank=True, max_length=500)),
                ('line_number', models.IntegerField(blank=True, null=True)),
                ('is_fixed', models.BooleanField(default=False)),
                ('fixed_at', models.DateTimeField(blank=True, null=True)),
                ('fix_description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='security_logs', to='marketplace.siteregistry')),
            ],
            options={
                'ordering': ['-severity', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='securitylog',
            index=models.Index(fields=['category', 'severity'], name='marketplace_categor_ffd254_idx'),
        ),
        migrations.AddIndex(
            model_name='securitylog',
            index=models.Index(fields=['is_fixed'], name='marketplace_is_fixe_603c08_idx'),
        ),
        
        # ============================================================
        # 5. PredictionLog Model
        # ============================================================
        migrations.CreateModel(
            name='PredictionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prediction_type', models.CharField(choices=[('traffic', 'Traffic Prediction'), ('seo', 'SEO Score Prediction'), ('sales', 'Sales Prediction'), ('growth', 'Growth Prediction')], max_length=20)),
                ('predicted_value', models.FloatField()),
                ('actual_value', models.FloatField(blank=True, null=True)),
                ('confidence_score', models.FloatField(default=0.0, help_text='0-100')),
                ('input_data', models.JSONField(default=dict, help_text='ትንበያው የተሰራበት መረጃ')),
                ('model_version', models.CharField(blank=True, max_length=50)),
                ('predicted_at', models.DateTimeField(auto_now_add=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='predictions', to='marketplace.siteregistry')),
            ],
            options={
                'ordering': ['-predicted_at'],
            },
        ),
        migrations.AddIndex(
            model_name='predictionlog',
            index=models.Index(fields=['prediction_type', 'site'], name='marketplace_predict_17d121_idx'),
        ),
        migrations.AddIndex(
            model_name='predictionlog',
            index=models.Index(fields=['-predicted_at'], name='marketplace_predict_5bd771_idx'),
        ),
        
        # ============================================================
        # 6. ExternalAPI Model
        # ============================================================
        migrations.CreateModel(
            name='ExternalAPI',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('api_type', models.CharField(choices=[('google_analytics', 'Google Analytics'), ('google_search_console', 'Google Search Console'), ('mailchimp', 'Mailchimp'), ('twilio', 'Twilio'), ('social_media', 'Social Media')], max_length=25)),
                ('name', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('error', 'Error'), ('rate_limited', 'Rate Limited')], default='active', max_length=20)),
                ('api_key', models.CharField(blank=True, max_length=255)),
                ('api_secret', models.CharField(blank=True, max_length=255)),
                ('base_url', models.URLField(blank=True)),
                ('webhook_url', models.URLField(blank=True)),
                ('rate_limit', models.IntegerField(default=100, help_text='በደቂቃ ጥሪዎች')),
                ('calls_made', models.IntegerField(default=0)),
                ('last_reset', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='external_apis', to='marketplace.siteregistry')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('api_type', 'site')},
            },
        ),
        
        # ============================================================
        # 7. UserSearch Model
        # ============================================================
        migrations.CreateModel(
            name='UserSearch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=255)),
                ('results_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        
        # ============================================================
        # 8. MarketTrend Model
        # ============================================================
        migrations.CreateModel(
            name='MarketTrend',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('niche_name', models.CharField(max_length=100)),
                ('demand_level', models.IntegerField(default=50)),
                ('ai_suggestion', models.TextField()),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        
        # ============================================================
        # 9. TranslationQueue Model
        # ============================================================
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
        
        # ============================================================
        # 10. SellerProfile Model
        # ============================================================
        migrations.CreateModel(
            name='SellerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_name', models.CharField(blank=True, max_length=255)),
                ('phone_number', models.CharField(blank=True, max_length=20)),
                ('address', models.TextField(blank=True)),
                ('website', models.URLField(blank=True)),
                ('total_products', models.IntegerField(default=0)),
                ('total_sales', models.IntegerField(default=0)),
                ('total_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('rating', models.FloatField(default=0.0, help_text='0-5 ውጤት')),
                ('last_active', models.DateTimeField(auto_now=True)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='seller_profiles', to='marketplace.siteregistry')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='seller_profile', to='auth.user')),
            ],
        ),
    ]