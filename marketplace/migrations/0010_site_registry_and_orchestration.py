# EthAfri/marketplace/migrations/0010_full_business_growth_migration.py

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0009_agenterrorlog'),
    ]

    operations = [
        # ============================================================
        # 1. SiteRegistry ሰንጠረዥን መፍጠር (Multi-Site Orchestration)
        # ============================================================
        migrations.CreateModel(
            name='SiteRegistry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="የጣቢያው ልዩ ስም", max_length=100, unique=True)),
                ('display_name', models.CharField(help_text="የሚታየው ስም", max_length=200)),
                ('niche', models.CharField(help_text="የገበያ ኒች", max_length=100)),
                ('target_market', models.CharField(help_text="ዒላማ ገበያ", max_length=100)),
                ('repo_url', models.URLField(blank=True, help_text="የጂት ሪፖዚቶሪ አድራሻ")),
                ('repo_path', models.CharField(blank=True, help_text="የአካባቢው የጂት ፎልደር መንገድ", max_length=500)),
                ('deployment_url', models.URLField(blank=True, help_text="የተሰማራው ድረ-ገጽ አድራሻ")),
                ('competitor_urls', models.JSONField(default=list, help_text="የተወዳዳሪ ድረ-ገጾች ዝርዝር")),
                ('primary_keywords', models.JSONField(default=list, help_text="ዋና ቁልፍ ቃላት")),
                ('target_audience', models.TextField(blank=True, help_text="ዒላማ ተመልካች መግለጫ")),
                ('content_style', models.CharField(
                    choices=[
                        ('professional', 'Professional'),
                        ('casual', 'Casual'),
                        ('storytelling', 'Storytelling'),
                        ('educational', 'Educational'),
                    ],
                    default='professional',
                    help_text="የይዘት አጻጻፍ ዘይቤ",
                    max_length=50
                )),
                ('growth_level', models.IntegerField(
                    choices=[
                        (1, 'Local'),
                        (2, 'City'),
                        (3, 'Country'),
                        (4, 'Continent'),
                        (5, 'Global'),
                    ],
                    default=1,
                    help_text="የአሁኑ የእድገት ደረጃ"
                )),
                ('monthly_visitors', models.IntegerField(default=0, help_text="በወር ጎብኝዎች")),
                ('page_views', models.IntegerField(default=0, help_text="ጠቅላላ ገጽ እይታዎች")),
                ('total_sellers', models.IntegerField(default=0, help_text="ጠቅላላ ሻጮች ብዛት")),
                ('total_products', models.IntegerField(default=0, help_text="ጠቅላላ ምርቶች ብዛት")),
                ('monthly_revenue', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    help_text="በወር ገቢ",
                    max_digits=20,
                )),
                ('last_traffic_update', models.DateTimeField(blank=True, help_text="የመጨረሻ የትራፊክ መረጃ ማዘመኛ", null=True)),
                ('last_marketing_campaign', models.DateTimeField(blank=True, help_text="የመጨረሻ ግብይት ካምፔን ቀን", null=True)),
                ('pending_notifications', models.JSONField(default=list, help_text="ያልተላኩ ማሳወቂያዎች")),
                ('is_active', models.BooleanField(default=True, help_text="ጣቢያው ንቁ ነው?")),
                ('auto_update_enabled', models.BooleanField(default=True, help_text="ኤጀንቱ በራስ-ሰር ያሻሽለዋል?")),
                ('auto_marketing_enabled', models.BooleanField(default=True, help_text="ራስ-ሰር ግብይት ያድርግ?")),
                ('update_frequency', models.CharField(
                    choices=[
                        ('hourly', 'Hourly'),
                        ('daily', 'Daily'),
                        ('weekly', 'Weekly'),
                    ],
                    default='daily',
                    help_text="ምን ያህል ጊዜ እንደሚሻሻል",
                    max_length=20
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['name', 'is_active'], name='marketplace_name_8491f6_idx'),
                    models.Index(fields=['niche', 'target_market'], name='marketplace_niche_5073be_idx'),
                    models.Index(fields=['growth_level'], name='marketplace_growth_3b5c8f_idx'),
                ],
            },
        ),

        # ============================================================
        # 2. Category ላይ parent መጨመር
        # ============================================================
        migrations.AddField(
            model_name='category',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='subcategories',
                to='marketplace.category',
            ),
        ),

        # ============================================================
        # 3. Product ላይ አዲስ ሜዳዎች መጨመር
        # ============================================================
        migrations.AddField(
            model_name='product',
            name='seo_score',
            field=models.IntegerField(default=0, help_text="SEO ውጤት (0-100)"),
        ),
        migrations.AddField(
            model_name='product',
            name='view_count',
            field=models.IntegerField(default=0, help_text="የተመለከተው ብዛት"),
        ),
        migrations.AddField(
            model_name='product',
            name='inquiry_count',
            field=models.IntegerField(default=0, help_text="የጥያቄ ብዛት"),
        ),
        migrations.AddField(
            model_name='product',
            name='last_enhanced',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # ============================================================
        # 4. AIProjectBacklog ላይ አዲስ ሜዳዎች መጨመር
        # ============================================================
        migrations.AddField(
            model_name='aiprojectbacklog',
            name='task_type',
            field=models.CharField(
                choices=[
                    ('code', 'Code Development'),
                    ('seo', 'SEO Optimization'),
                    ('marketing', 'Marketing Campaign'),
                    ('acquisition', 'Customer Acquisition'),
                    ('growth', 'Growth Strategy'),
                    ('design', 'UI/UX Design'),
                    ('content', 'Content Creation'),
                ],
                default='code',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='aiprojectbacklog',
            name='estimated_hours',
            field=models.FloatField(default=1.0),
        ),
        migrations.AddField(
            model_name='aiprojectbacklog',
            name='complexity',
            field=models.IntegerField(default=1, help_text="1-10 (ቀላል እስከ ከባድ)"),
        ),
        migrations.AddField(
            model_name='aiprojectbacklog',
            name='site',
            field=models.ForeignKey(
                blank=True,
                help_text="ይህ ስራ የሚመለከተው የትኛውን ድረ-ገጽ ነው?",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='backlog_tasks',
                to='marketplace.siteregistry',
            ),
        ),
        migrations.AlterField(
            model_name='aiprojectbacklog',
            name='status',
            field=models.CharField(
                choices=[
                    ('Pending', 'Pending'),
                    ('Running', 'Running'),
                    ('Completed', 'Completed'),
                    ('Overridden', 'Overridden'),
                    ('Blocked', 'Blocked'),
                ],
                default='Pending',
                max_length=20,
            ),
        ),

        # ============================================================
        # 5. AIEvolutionLog ላይ አዲስ ሜዳዎች መጨመር
        # ============================================================
        migrations.AddField(
            model_name='aievolutionlog',
            name='improvement_metrics',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="SEO score, load time, etc."
            ),
        ),
        migrations.AddField(
            model_name='aievolutionlog',
            name='site',
            field=models.ForeignKey(
                blank=True,
                help_text="ይህ ለውጥ የሚመለከተው የትኛውን ድረ-ገጽ ነው?",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='evolution_logs',
                to='marketplace.siteregistry',
            ),
        ),

        # ============================================================
        # 6. AdminOverrideInstruction ላይ site ፎሬን-ኬይ መጨመር
        # ============================================================
        migrations.AddField(
            model_name='adminoverrideinstruction',
            name='site',
            field=models.ForeignKey(
                blank=True,
                help_text="ይህ መመሪያ የሚመለከተው የትኛውን ድረ-ገጽ ነው?",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='overrides',
                to='marketplace.siteregistry',
            ),
        ),

        # ============================================================
        # 7. AgentErrorLog ላይ አዲስ ሜዳዎች (site እና error_type) መጨመር
        # ============================================================
        migrations.AddField(
            model_name='agenterrorlog',
            name='site',
            field=models.ForeignKey(
                blank=True,
                help_text="ይህ ስህተት የተከሰተው በየትኛው ድረ-ገጽ ላይ ነው?",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='error_logs',
                to='marketplace.siteregistry',
            ),
        ),
        
        # ⚠️ ማሻሻያ፦ 'error_type' ቀደም ሲል በዳታቤዝ ውስጥ ስላልነበረ እዚህ 'AddField' (አዲስ መፍጠሪያ) ተደርጎ ተስተካክሏል! [1]
        migrations.AddField(
            model_name='agenterrorlog',
            name='error_type',
            field=models.CharField(
                choices=[
                    ('syntax', 'Syntax Error'),
                    ('runtime', 'Runtime Error'),
                    ('import', 'Import Error'),
                    ('logic', 'Logic Error'),
                    ('api', 'API Error'),
                    ('deployment', 'Deployment Error'),
                    ('database', 'Database Error'),
                ],
                default='syntax',
                max_length=20,
            ),
        ),

        # ============================================================
        # 8. CustomerAcquisitionLog ሞዴል መፍጠር
        # ============================================================
        migrations.CreateModel(
            name='CustomerAcquisitionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(
                    choices=[
                        ('email', 'Email'),
                        ('sms', 'SMS'),
                        ('social', 'Social Media'),
                        ('referral', 'Referral'),
                        ('organic', 'Organic'),
                        ('paid', 'Paid Advertising'),
                    ],
                    max_length=20,
                )),
                ('contact_info', models.CharField(help_text="ኢሜይል ወይም ስልክ ቁጥር", max_length=255)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('message_sent', models.TextField(blank=True)),
                ('response_received', models.BooleanField(default=False)),
                ('converted_to_seller', models.BooleanField(default=False)),
                ('converted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('site', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='acquisition_logs',
                    to='marketplace.siteregistry',
                )),
            ],
        ),

        # ============================================================
        # 9. MarketingCampaign ሞዴል መፍጠር
        # ============================================================
        migrations.CreateModel(
            name='MarketingCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('campaign_type', models.CharField(
                    choices=[
                        ('email_blast', 'Email Blast'),
                        ('sms_blast', 'SMS Blast'),
                        ('social_post', 'Social Media Post'),
                        ('seo_campaign', 'SEO Campaign'),
                        ('referral', 'Referral Program'),
                    ],
                    max_length=20,
                )),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'Draft'),
                        ('scheduled', 'Scheduled'),
                        ('running', 'Running'),
                        ('completed', 'Completed'),
                        ('paused', 'Paused'),
                    ],
                    default='draft',
                    max_length=20,
                )),
                ('subject', models.CharField(blank=True, max_length=255)),
                ('message', models.TextField()),
                ('target_audience', models.JSONField(default=dict, help_text="ዒላማ ተመልካች መስፈርቶች")),
                ('total_sent', models.IntegerField(default=0)),
                ('total_opened', models.IntegerField(default=0)),
                ('total_clicked', models.IntegerField(default=0)),
                ('total_converted', models.IntegerField(default=0)),
                ('scheduled_at', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='marketing_campaigns',
                    to='marketplace.siteregistry',
                )),
            ],
        ),

        # ============================================================
        # 10. SellerProfile ሞዴል መፍጠር
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
                ('rating', models.FloatField(default=0.0, help_text="0-5 ውጤት")),
                ('last_active', models.DateTimeField(auto_now=True)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('site', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='seller_profiles',
                    to='marketplace.siteregistry',
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='seller_profile',
                    to='auth.user',
                )),
            ],
        ),

        # ============================================================
        # 11. NotificationQueue ሞዴል መፍጠር
        # ============================================================
        migrations.CreateModel(
            name='NotificationQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(
                    choices=[
                        ('email', 'Email'),
                        ('sms', 'SMS'),
                        ('push', 'Push Notification'),
                        ('in_app', 'In-App Notification'),
                    ],
                    max_length=20,
                )),
                ('recipient', models.CharField(help_text="ኢሜይል ወይም ስልክ ቁጥር", max_length=255)),
                ('subject', models.CharField(blank=True, max_length=255)),
                ('message', models.TextField()),
                ('is_sent', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('site', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to='marketplace.siteregistry',
                )),
            ],
        ),
    ]