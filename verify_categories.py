import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.models import Transacao, Categoria, Casa
from django.db.models import Sum, Count

casa = Casa.objects.first()
primeiro_dia = datetime(datetime.now().year, datetime.now().month, 1).date()

print("📊 Verificando transações de despesa no mês atual:")
print()

transacoes = Transacao.objects.filter(
    casa=casa,
    tipo='despesa',
    data__gte=primeiro_dia,
    status='paga'
).select_related('categoria').order_by('categoria__nome')

print(f"Total de transações: {transacoes.count()}")
print()

# Agrupar por categoria
for t in transacoes:
    cat_nome = t.categoria.nome if t.categoria else "Sem categoria"
    cat_cor = t.categoria.cor if t.categoria else "N/A"
    print(f"- {t.titulo}: R$ {t.valor:.2f} | Categoria: '{cat_nome}' (ID: {t.categoria.id if t.categoria else 'N/A'}, Cor: {cat_cor})")

print()
print("📋 Verificando todas as categorias de despesa:")
categorias = Categoria.objects.filter(casa=casa, tipo='despesa').order_by('nome')
print(f"Total de categorias: {categorias.count()}")
print()

# Agrupar por nome
from collections import defaultdict
nomes = defaultdict(list)
for cat in categorias:
    nomes[cat.nome.lower()].append((cat.id, cat.nome, cat.cor))

print("Categorias agrupadas por nome:")
for nome_lower, cats in sorted(nomes.items()):
    if len(cats) > 1:
        print(f"⚠️ DUPLICATA: '{nome_lower}' tem {len(cats)} registros:")
        for cat_id, cat_nome, cat_cor in cats:
            print(f"   - ID {cat_id}: '{cat_nome}' (Cor: {cat_cor})")
    else:
        cat_id, cat_nome, cat_cor = cats[0]
        print(f"✅ '{cat_nome}' - ID: {cat_id} (Cor: {cat_cor})")
