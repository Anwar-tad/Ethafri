# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/migrations/0013_build_phase_and_trigger_rules.py
# 📝 ለውጥ፦ Build Phase + Real Counters + Trigger Fields
# 📅 ቀን፦ 2026-06-21
# ============================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0012_advanced_agent_features'),
    ]

    operations = [
        # ============================================================
        # 1. SiteRegistry ላይ አዲስ ሜዳዎች
        # ============================================================
        migrations.AddField(
            model_name='siteregistry',
            name='build_phase',
            field=models.IntegerField(
                default=0,
                help_text='0=Scaffolding, 1=Real Data, 2=Core Features, 3=Engagement, 4=Monetization, 5=Mature'
            ),
        ),
        migrations.AddField(
            model_name='siteregistry',
            name='real_product_count',
            field=models.IntegerField(default=0, help_text='እውነተኛ ምርቶች ብዛት'),
        ),
        migrations.AddField(
            model_name='siteregistry',
            name='real_customer_count',
            field=models.IntegerField(default=0, help_text='እውነተኛ ደንበኞች ብዛት'),
        ),
        migrations.AddField(
            model_name='siteregistry',
            name='phase_transition_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='siteregistry',
            index=models.Index(fields=['build_phase'], name='marketplace_build_p_601caa_idx'),
        ),

        # ============================================================
        # 2. AIProjectBacklog ላይ አዲስ ሜዳዎች
        # ============================================================
        migrations.AddField(
            model_name='aiprojectbacklog',
            name='business_impact_score',
            field=models.IntegerField(default=5, help_text='1-10: የንግድ ተጽዕኖ ውጤት'),
        ),
        migrations.AddField(
            model_name='aiprojectbacklog',
            name='trigger_condition',
            field=models.CharField(blank=True, help_text='ይህ ስራ የተፈጠረበት ትሪገር ሁኔታ', max_length=255),
        ),
    ]