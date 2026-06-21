from django.db import models
from django.contrib.auth.models import User

class VectorMemory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    embedding = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplace_vectormemory'
        
    def __str__(self):
        return f"VectorMemory {self.id} for {self.user}"