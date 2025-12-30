import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.models import Transacao, Categoria, Casa
from django.db.models import Sum, OuterRef, Subquery

casa = Casa.objects.first()
primeiro_dia = datetime(datetime.now().year, datetime.now().month, 1).date()

print(f"🏠 Casa: {casa.nome}")
print(f"📅 Período: {primeiro_dia} até hoje")
print()

# Verificar TODAS as transações de despesa do mês
print("📊 TODAS as transações de despesa deste mês:")
todas = Transacao.objects.filter(
    casa=casa,
    tipo='despesa',
    data__gte=primeiro_dia
).select_related('categoria').order_by('status', 'categoria__nome')

print(f"Total: {todas.count()}")
print()

for t in todas:
    cat_nome = t.categoria.nome if t.categoria else "Sem categoria"
    cat_id = t.categoria.id if t.categoria else "N/A"
    print(f"[{t.status.upper()}] {t.titulo}: R$ {t.valor:.2f} | Categoria: '{cat_nome}' (ID: {cat_id})")

print()
print("="*70)
print()

# Query que está sendo usada no dashboard
print("📈 Query do Dashboard (valores agrupados):")
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

despesas_por_categoria = list(despesas_por_categoria)

print(f"Total de grupos: {len(despesas_por_categoria)}")
print()

for item in despesas_por_categoria:
    print(f"✅ {item['categoria__nome']}: R$ {item['total']:.2f} (Cor: {item['cor']})")
