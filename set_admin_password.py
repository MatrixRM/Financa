import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.models import Usuario

try:
    admin = Usuario.objects.get(username='admin')
    admin.set_password('admin123')
    admin.save()
    print('Senha do admin definida como: admin123')
except Usuario.DoesNotExist:
    print('Usuário admin não encontrado!')
