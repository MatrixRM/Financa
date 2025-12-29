#!/usr/bin/env python
"""Script para verificar e limpar transações duplicadas do chat."""

import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from core.models import Transacao

def main():
    hoje = datetime.now().date()
    
    print("\n📋 Transações criadas hoje:")
    print("=" * 70)
    
    transacoes = Transacao.objects.filter(data=hoje).order_by('-criada_em')
    
    # Agrupar por descrição similar
    grupos = {}
    for t in transacoes:
        chave = f"{t.titulo.lower().strip()} - R$ {t.valor}"
        if chave not in grupos:
            grupos[chave] = []
        grupos[chave].append(t)
    
    duplicatas = []
    for chave, lista in grupos.items():
        if len(lista) > 1:
            duplicatas.extend(lista)
            print(f"\n⚠️  DUPLICADAS ({len(lista)}x): {chave}")
            for t in lista:
                print(f"   ID {t.id} - {t.criada_em.strftime('%H:%M:%S')}")
        else:
            t = lista[0]
            print(f"\n✅ ID {t.id}: {t.titulo} - R$ {t.valor}")
            print(f"   Criado: {t.criada_em.strftime('%H:%M:%S')}")
    
    print("\n" + "=" * 70)
    print(f"Total: {len(transacoes)} transações")
    print(f"Duplicadas: {len(duplicatas)} ({len(duplicatas) - len(set(chave for chave in grupos if len(grupos[chave]) > 1))} podem ser removidas)")
    
    if duplicatas:
        print("\n💡 Para remover duplicatas, mantenha apenas a primeira de cada grupo")
        resposta = input("\nRemover duplicatas automaticamente? (s/N): ")
        
        if resposta.lower() == 's':
            removidas = 0
            for chave, lista in grupos.items():
                if len(lista) > 1:
                    # Manter a primeira, remover as outras
                    for t in lista[1:]:
                        print(f"   🗑️  Removendo ID {t.id}")
                        t.delete()
                        removidas += 1
            
            print(f"\n✅ {removidas} transações duplicadas removidas!")

if __name__ == '__main__':
    main()
