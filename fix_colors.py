import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.models import Categoria

# Paleta de cores vibrantes
CORES_DESPESAS = [
    '#dc3545',  # Vermelho
    '#fd7e14',  # Laranja
    '#ffc107',  # Amarelo
    '#20c997',  # Teal
    '#0dcaf0',  # Cyan
    '#6f42c1',  # Roxo
    '#d63384',  # Pink
    '#6c757d',  # Cinza
    '#e83e8c',  # Magenta
    '#17a2b8',  # Info
]

CORES_RECEITAS = [
    '#198754',  # Verde
    '#20c997',  # Teal claro
    '#0d6efd',  # Azul
    '#0dcaf0',  # Cyan
    '#6610f2',  # Indigo
    '#6f42c1',  # Roxo
    '#28a745',  # Verde claro
    '#17a2b8',  # Info
]

print("=== Corrigindo Cores das Categorias ===\n")

categorias_despesa = Categoria.objects.filter(tipo='despesa')
categorias_receita = Categoria.objects.filter(tipo='receita')

updated = 0

print("📝 Atualizando despesas...")
for i, cat in enumerate(categorias_despesa):
    cor = CORES_DESPESAS[i % len(CORES_DESPESAS)]
    if cat.cor != cor:
        cat.cor = cor
        cat.save()
        print(f"   ✅ {cat.nome}: {cor}")
        updated += 1

print("\n📝 Atualizando receitas...")
for i, cat in enumerate(categorias_receita):
    cor = CORES_RECEITAS[i % len(CORES_RECEITAS)]
    if cat.cor != cor:
        cat.cor = cor
        cat.save()
        print(f"   ✅ {cat.nome}: {cor}")
        updated += 1

print(f"\n✅ {updated} categorias atualizadas!")
print("🔄 Recarregue a página para ver as mudanças.")
