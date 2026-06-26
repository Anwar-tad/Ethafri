# ============================================================
# 📁 ፋይል፦ EthAfri/purge_fake_data.py
# 📝 ዓላማ፦ Safe Database Purge — Fresh Start for v9.5 Agent
# ============================================================

import os
import django

# 1. Django ቅንብርን ማግኘት
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from marketplace.models import (
    Product, Category, SiteRegistry, AIProjectBacklog, 
    SecurityLog, AgentErrorLog, AIEvolutionLog, VectorMemory, 
    SelfHealingLog, SellerProfile, NotificationQueue
)

def purge_database():
    print("🧹 Purging old AI fake data from the database...")
    
    # የውሸት ምርቶችን እና ሻጮችን ማጽዳት
    Product.objects.all().delete()
    SellerProfile.objects.all().delete()
    NotificationQueue.objects.all().delete()
    
    # የድሮ የኤጀንት መዝገቦችን በሙሉ ማጽዳት
    AIProjectBacklog.objects.all().delete()
    SecurityLog.objects.all().delete()
    AgentErrorLog.objects.all().delete()
    AIEvolutionLog.objects.all().delete()
    VectorMemory.objects.all().delete()
    SelfHealingLog.objects.all().delete()
    
    # የጣቢያዎች መዝገብን ማጽዳት (primary ብቻ እንዲቀር ማድረግ)
    SiteRegistry.objects.all().delete()
    
    # 2. የ 'primary' ሳይት መዝገብን በንጽህና መፍጠር (Auto-Bootstrapping)
    SiteRegistry.objects.create(
        name="primary",
        display_name="EthAfri Primary",
        niche="general",
        target_market="Global",
        is_active=True,
        build_phase=0
    )
    
    print("✅ Database successfully purged! Registered fresh 'primary' site registry.")
    print("🤖 You can now run the agent cleanly using: python manage.py run_agent")

if __name__ == "__main__":
    purge_database()