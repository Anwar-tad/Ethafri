from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0008_backlog_dependency_fix'), # የዚህን ስም ካለፈው ማይግሬሽንህ ጋር አዛምደው
    ]

    operations = [
        migrations.CreateModel(
            name='AgentErrorLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=255)),
                ('error_message', models.TextField(help_text="የተፈጠረው የስህተት አይነት (Traceback)")),
                ('code_attempted', models.TextField(help_text="ኤጀንቱ የሞከረው የኮድ ክፍል")),
                ('correction_applied', models.TextField(blank=True, null=True, help_text="ስህተቱን ለማስተካከል የተጠቀመበት አዲስ ኮድ")),
                ('resolved', models.BooleanField(default=False, help_text="ችግሩ ተፈቷል?")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
