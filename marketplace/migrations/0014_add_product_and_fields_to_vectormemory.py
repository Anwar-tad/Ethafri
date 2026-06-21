# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/migrations/0014_add_product_and_fields_to_vectormemory.py
# 📝 ለውጥ፦ VectorMemory ላይ አዲስ ሜዳዎች መጨመር
# 📅 ቀን፦ 2026-06-21
# ============================================================

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0013_build_phase_and_trigger_rules'),
    ]

    operations = [
        # ============================================================
        # 1. VectorMemory ላይ product ForeignKey መጨመር
        # ============================================================
        migrations.AddField(
            model_name='vectormemory',
            name='product',
            field=models.ForeignKey(
                blank=True,
                help_text='The product this vector memory is associated with.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='vector_memories',
                to='marketplace.product',
            ),
        ),
        
        # ============================================================
        # 2. VectorMemory ላይ text_content መጨመር
        # ============================================================
        migrations.AddField(
            model_name='vectormemory',
            name='text_content',
            field=models.TextField(
                blank=True,
                help_text='The original text content that was vectorized.'
            ),
        ),
        
        # ============================================================
        # 3. VectorMemory ላይ vector_data መጨመር
        # ============================================================
        migrations.AddField(
            model_name='vectormemory',
            name='vector_data',
            field=models.JSONField(
                default=dict,
                help_text='JSON representation of the vector embedding.'
            ),
        ),
        
        # ============================================================
        # 4. VectorMemory ላይ embedding_model መጨመር
        # ============================================================
        migrations.AddField(
            model_name='vectormemory',
            name='embedding_model',
            field=models.CharField(
                default='default-embedding-model',
                help_text='The name or identifier of the embedding model used to generate this vector.',
                max_length=100,
            ),
        ),
        
        # ============================================================
        # 5. VectorMemory ላይ created_at እና updated_at መጨመር
        # ============================================================
        migrations.AddField(
            model_name='vectormemory',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='vectormemory',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        
        # ============================================================
        # 6. VectorMemory ላይ ኢንዴክሶች መጨመር
        # ============================================================
        migrations.AddIndex(
            model_name='vectormemory',
            index=models.Index(fields=['product'], name='marketplace_product_771a46_idx'),
        ),
        migrations.AddIndex(
            model_name='vectormemory',
            index=models.Index(fields=['embedding_model'], name='marketplace_embeddi_3bb1ff_idx'),
        ),
        
        # ============================================================
        # 7. AgentTask ላይ metadata መጨመር
        # ============================================================
        migrations.AddField(
            model_name='agenttask',
            name='metadata',
            field=models.JSONField(blank=True, default=dict, help_text='Additional task metadata'),
        ),
    ]