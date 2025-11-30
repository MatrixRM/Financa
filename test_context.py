#!/usr/bin/env python
"""Script para testar contexto de conversa."""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.services.openai_client import OpenAIClient

print("=" * 80)
print("🧪 TESTE DE CONTEXTO DE CONVERSA")
print("=" * 80)

client = OpenAIClient()

# Simular conversa com clarificação
print("\n📝 CONVERSA 1: Usuário fornece valor, IA pede categoria")
print("-" * 80)

# Mensagem inicial
msg1 = "gastei vinte pila"
print(f"User: {msg1}")
result1 = client.parse_user_message(msg1, [])
print(f"Assistant: {result1['assistant_message']}")
print(f"Clarification needed: {result1['clarification_needed']}")
print(f"Transaction data: {result1.get('transaction', {})}")

# Construir contexto
context = [
    {'role': 'user', 'content': msg1},
    {'role': 'assistant', 'content': result1['assistant_message']}
]

# Resposta do usuário
msg2 = "mercado"
print(f"\nUser: {msg2}")
result2 = client.parse_user_message(msg2, context)
print(f"Assistant: {result2['assistant_message']}")
print(f"Clarification needed: {result2['clarification_needed']}")
print(f"Transaction data: {result2.get('transaction', {})}")

if result2.get('transaction', {}).get('amount'):
    print(f"\n✅ SUCESSO! IA completou a transação:")
    print(f"   - Valor: R$ {result2['transaction']['amount']}")
    print(f"   - Categoria: {result2['transaction'].get('category', 'N/A')}")
else:
    print(f"\n❌ FALHOU! IA não conseguiu completar a transação")

print("\n" + "=" * 80)
print("\n📝 CONVERSA 2: Teste com descrição e conta")
print("-" * 80)

msg3 = "comprei por 50 reais"
print(f"User: {msg3}")
result3 = client.parse_user_message(msg3, [])
print(f"Assistant: {result3['assistant_message']}")
print(f"Clarification needed: {result3['clarification_needed']}")

context2 = [
    {'role': 'user', 'content': msg3},
    {'role': 'assistant', 'content': result3['assistant_message']}
]

msg4 = "gasolina no cartão"
print(f"\nUser: {msg4}")
result4 = client.parse_user_message(msg4, context2)
print(f"Assistant: {result4['assistant_message']}")
print(f"Clarification needed: {result4['clarification_needed']}")
print(f"Transaction data: {result4.get('transaction', {})}")

if result4.get('transaction', {}).get('amount'):
    print(f"\n✅ SUCESSO! IA completou a transação:")
    print(f"   - Valor: R$ {result4['transaction']['amount']}")
    print(f"   - Categoria/Título: {result4['transaction'].get('category', result4['transaction'].get('title', 'N/A'))}")
    print(f"   - Conta: {result4['transaction'].get('account', 'N/A')}")
else:
    print(f"\n❌ FALHOU! IA não conseguiu completar a transação")

print("\n" + "=" * 80)
