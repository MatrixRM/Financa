import os
import django
from datetime import datetime

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.models import Transacao, Categoria, Casa
from django.db.models import Sum, OuterRef, Subquery
from decimal import Decimal

# Get the first casa
casa = Casa.objects.first()
if not casa:
    print("❌ Nenhuma casa encontrada")
    exit()

print(f"🏠 Casa: {casa.nome}")
print()

# Get first day of current month
primeiro_dia = datetime(datetime.now().year, datetime.now().month, 1).date()
print(f"📅 Período: {primeiro_dia} até hoje")
print()

# Query despesas por categoria
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

print("📊 Despesas por categoria:")
print(f"Total de registros: {len(despesas_por_categoria)}")
print()

if len(despesas_por_categoria) == 0:
    print("⚠️ NENHUMA DESPESA ENCONTRADA!")
    print("\nVerificando transações no sistema...")
    
    all_transacoes = Transacao.objects.filter(casa=casa, tipo='despesa')
    print(f"Total de despesas (todas): {all_transacoes.count()}")
    
    transacoes_pagas = Transacao.objects.filter(casa=casa, tipo='despesa', status='paga')
    print(f"Total de despesas pagas: {transacoes_pagas.count()}")
    
    transacoes_mes = Transacao.objects.filter(casa=casa, tipo='despesa', data__gte=primeiro_dia)
    print(f"Total de despesas no mês: {transacoes_mes.count()}")
    
    if transacoes_pagas.count() > 0:
        print("\n📝 Últimas 5 despesas pagas:")
        for t in transacoes_pagas[:5]:
            print(f"  - {t.descricao}: R$ {t.valor:.2f} (Data: {t.data}, Status: {t.status})")
else:
    for item in despesas_por_categoria:
        categoria = item['categoria__nome'] or '(Sem categoria)'
        total = item['total']
        cor = item['cor'] or '#6c757d'
        print(f"✅ {categoria}: R$ {total:.2f} - Cor: {cor}")
