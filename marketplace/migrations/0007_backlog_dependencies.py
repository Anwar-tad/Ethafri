# EthAfri/marketplace/migrations/0007_backlog_dependencies.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        # ⚠️ ከዚህ በፊት የተገነባው ማይግሬሽንህ ስም '0006_autonomous_architecture' መሆኑን አረጋግጥ
        ('marketplace', '0006_autonomous_architecture'), 
    ]

    operations = [
        migrations.AddField(
            model_name='aiprojectbacklog',
            name='dependency',
            field=models.ForeignKey(
                blank=True, 
                help_text='ይህ ስራ ከመሰራቱ በፊት አስቀድሞ መጠናቀቅ ያለበት ሌላ የባክሎግ ስራ (የስራዎች ጥገኝነት)', 
                null=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                related_name='dependent_tasks', 
                to='marketplace.aiprojectbacklog'
            ),
        ),
    ]
    
    