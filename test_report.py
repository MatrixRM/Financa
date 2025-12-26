#!/usr/bin/env python
"""Script para testar geração de relatórios localmente."""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.services.openai_client import OpenAIClient

User = get_user_model()
user = User.objects.first()

if not user:
    print("❌ Nenhum usuário encontrado")
    exit(1)

print("=" * 80)
print("🧪 TESTE DE GERAÇÃO DE RELATÓRIOS")
print("=" * 80)

# Criar cliente OpenAI
client = OpenAIClient()

# Testar pedido de relatório
test_messages = [
    "Me mostre um relatório deste mês",
    "Pode gerar um relatório pra mim desse mês?",
    "Quanto gastei esse mês?",
    "Resumo das minhas finanças"
]

for msg in test_messages:
    print(f"\n📝 Testando: '{msg}'")
    print("-" * 80)
    
    try:
        result = client.parse_user_message(msg, [])
        
        print(f"✓ Intent: {result.get('intent')}")
        print(f"✓ Clarification needed: {result.get('clarification_needed')}")
        print(f"✓ Assistant message: {result.get('assistant_message')[:100]}...")
        
        if result.get('query'):
            print(f"✓ Query: {json.dumps(result['query'], indent=2)}")
        
        if result.get('intent') == 'report_request':
            print("✅ IA identificou corretamente como pedido de relatório")
        else:
            print(f"⚠️ IA identificou como: {result.get('intent')}")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print()

print("=" * 80)
print("\n💡 PRÓXIMO PASSO:")
print("Faça o deploy no PythonAnywhere:")
print("  cd ~/Financa")
print("  git pull origin main")
print("  # Aguardar reload automático ou executar manualmente")
print("=" * 80)
