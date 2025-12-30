import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.models import Categoria

print("=== Verificando Cores das Categorias ===\n")

categorias = Categoria.objects.all()

if not categorias.exists():
    print("❌ Nenhuma categoria encontrada no banco!")
else:
    print(f"✅ {categorias.count()} categorias encontradas:\n")
    
    sem_cor = []
    com_cor = []
    
    for cat in categorias:
        if not cat.cor or cat.cor == '#6c757d':
            sem_cor.append(cat)
            print(f"❌ {cat.nome} ({cat.tipo}) - Sem cor ou cor padrão: {cat.cor}")
        else:
            com_cor.append(cat)
            print(f"✅ {cat.nome} ({cat.tipo}) - Cor: {cat.cor}")
    
    print(f"\n📊 Resumo:")
    print(f"   Com cor definida: {len(com_cor)}")
    print(f"   Sem cor/padrão: {len(sem_cor)}")
    
    if sem_cor:
        print(f"\n💡 Sugestão: Adicionar cores para {len(sem_cor)} categorias")
        print("   Execute: python fix_colors.py")
