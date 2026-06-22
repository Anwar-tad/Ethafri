# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/migrations/0012_advanced_agent_features.py
# 📝 ለውጥ፦ Advanced Agent Features — VectorMemory, AgentTask, ABTest, SecurityLog, PredictionLog, ExternalAPI
# 📅 ቀን፦ 2026-06-22
# ============================================================

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0011_product_site_link'),
    ]

    operations = [
        # ============================================================
        # 1. VectorMemory ሞዴል
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
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='memory_entries', to='marketplace.siteregistry')),
                ('related_task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='memory_entries', to='marketplace.aiprojectbacklog')),
            ],
            options={
                'ordering': ['-success_rate', '-usage_count'],
                'indexes': [
                    models.Index(fields=['memory_type', 'site'], name='marketplace_memory_ab2c6c_idx'),
                    models.Index(fields=['-created_at'], name='marketplace_memory_20162d_idx'),
                ],
            },
        ),

        # ============================================================
        # 2. AgentTask ሞዴል
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
                'indexes': [
                    models.Index(fields=['agent_type', 'status'], name='marketplace_agentty_847321_idx'),
                    models.Index(fields=['site', 'status'], name='marketplace_site_id_6bde06_idx'),
                ],
            },
        ),

        # ============================================================
        # 3. ABTest ሞዴል
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
        # 4. SecurityLog ሞዴል
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
                'indexes': [
                    models.Index(fields=['category', 'severity'], name='marketplace_security_128a46_idx'),
                    models.Index(fields=['is_fixed'], name='marketplace_security_840055_idx'),
                ],
            },
        ),

        # ============================================================
        # 5. PredictionLog ሞዴል
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
                'indexes': [
                    models.Index(fields=['prediction_type', 'site'], name='marketplace_predicti_9ce3e9_idx'),
                    models.Index(fields=['-predicted_at'], name='marketplace_predicti_1a7d5d_idx'),
                ],
            },
        ),

        # ============================================================
        # 6. ExternalAPI ሞዴል
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
    ]