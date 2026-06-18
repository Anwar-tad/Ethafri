# EthAfri/marketplace/migrations/0006_autonomous_architecture.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0005_owner_directive'),  # ካንተ የመጨረሻ ማይግሬሽን ቀጥሎ እንዲሰካ
    ]

    operations = [
        # 1. AIProjectBacklog ሰንጠረዥን መፍጠር
        migrations.CreateModel(
            name='AIProjectBacklog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=255)),
                ('target_file', models.CharField(help_text='የሚሻሻለው ወይም የሚመረመረው የኮድ ፋይል ስም', max_length=255)),
                ('priority', models.CharField(choices=[('Critical', 'Critical'), ('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], default='Medium', max_length=20)),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('Running', 'Running'), ('Completed', 'Completed'), ('Overridden', 'Overridden')], default='Pending', max_length=20)),
                ('description', models.TextField(blank=True, default='', help_text='የስራው ዝርዝር መግለጫ እና ቅድሚያ የተሰጠበት ምክንያት')),
                ('task_hash', models.CharField(blank=True, help_text='የስራ መደራረብን ለመከላከል በራስ-ሰር የሚመነጭ ልዩ ሃሽ', max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        
        # 2. AIEvolutionLog ሰንጠረዥን መፍጠር
        migrations.CreateModel(
            name='AIEvolutionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target_file', models.CharField(max_length=255)),
                ('reason_for_change', models.TextField()),
                ('old_code_backup', models.TextField(blank=True, help_text='የነበረው የድሮው ኮድ', null=True)),
                ('new_code_patch', models.TextField(blank=True, help_text='የተተካው አዲሱ ኮድ', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('backlog_task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='evolution_logs', to='marketplace.aiprojectbacklog')),
            ],
        ),
        
        # 3. AdminOverrideInstruction ሰንጠረዥን መፍጠር
        migrations.CreateModel(
            name='AdminOverrideInstruction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instruction', models.TextField(help_text='ለኤጀንቱ የሚተላለፈው የባለቤት ትዕዛዝ')),
                ('priority_override', models.CharField(blank=True, choices=[('Critical', 'Critical'), ('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], help_text='የስራውን ቅድሚያ ደረጃ ለመቀየር ከተፈለገ', max_length=20, null=True)),
                ('is_processed', models.BooleanField(default=False, help_text='ኤጀንቱ መመሪያውን አንብቦ ተግባራዊ አድርጎታል?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('backlog_task', models.ForeignKey(blank=True, help_text='ይህ መመሪያ የሚመለከተው የተወሰነ የባክሎግ ስራ ካለ (ባዶ ከሆነ ለአጠቃላይ ሲስተም ያገለግላል)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='overrides', to='marketplace.aiprojectbacklog')),
            ],
        ),
    ]
