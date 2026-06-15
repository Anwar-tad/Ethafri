import os
import django

# የዲጃንጎ ሲስተምን ማስጀመር
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

# የእርስዎ መረጃ
username = 'Anwar'
email = 'ilvuma11@gmail.com'
password = 'A555098@r'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Superuser {username} created successfully!")
else:
    print(f"Superuser {username} already exists.")