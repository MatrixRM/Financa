import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.models import Transacao, Categoria, Casa
from django.db.models import Sum, OuterRef, Subquery
from datetime import datetime

casa = Casa.objects.first()
primeiro_dia = datetime(datetime.now().year, datetime.now().month, 1).date()

despesas_por_categoria = Transacao.objects.filter(
    casa=casa,
    tipo='despesa',
    data__gte=primeiro_dia,
    status='paga'
).values('categoria__nome').annotate(
    total=Sum('valor'),
    cor=Subquery(
        Categoria.objects.filter(
            nome=OuterRef('categoria__nome'),
            casa=casa
        ).values('cor')[:1]
    )
).order_by('-total')[:10]

print("📊 Testando acesso aos campos:")
print()
for item in despesas_por_categoria:
    print(f"Tipo: {type(item)}")
    print(f"Keys: {item.keys()}")
    print(f"categoria__nome: {item.get('categoria__nome')}")
    print(f"total: {item.get('total')}")
    print(f"cor: {item.get('cor')}")
    print()
    break
