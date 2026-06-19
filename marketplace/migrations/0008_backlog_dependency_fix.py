# marketplace/migrations/0008_backlog_dependency_fix.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0007_backlog_dependencies'), 
    ]

    operations = [
        # ይህ ኦፕሬሽን ባክሎግ ላይ ለሚፈለገው የ 'dependency' ፊልድ ማይግሬሽን ይፈጥራል
        migrations.AlterField(
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
