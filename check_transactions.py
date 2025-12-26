#!/usr/bin/env python
"""Script para verificar transações e histórico do chat."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.models import Transacao, ChatHistory
from django.contrib.auth import get_user_model
from datetime import date, timedelta

User = get_user_model()
user = User.objects.first()

print("=" * 80)
print("🔍 VERIFICAÇÃO DE TRANSAÇÕES E HISTÓRICO")
print("=" * 80)

# Verificar transações recentes
print("\n📊 Transações dos últimos 7 dias:")
print("-" * 80)
hoje = date.today()
inicio = hoje - timedelta(days=7)
trans = Transacao.objects.filter(
    casa=user.casa,
    data__gte=inicio
).order_by('-data', '-id')

if trans.exists():
    for t in trans:
        print(f"{t.data} | {t.titulo[:30]:30} | {t.categoria.nome[:20]:20} | R$ {t.valor:8.2f} | {t.conta.nome}")
else:
    print("❌ Nenhuma transação encontrada nos últimos 7 dias")

# Verificar histórico do chat
print("\n\n💬 Últimas 15 mensagens do chat:")
print("-" * 80)
hist = ChatHistory.objects.filter(usuario=user).order_by('-created_at')[:15]

if hist.exists():
    for h in hist:
        hora = h.created_at.strftime("%H:%M")
        intent = h.intent or 'N/A'
        user_msg = h.user_message[:50] if len(h.user_message) > 50 else h.user_message
        bot_msg = h.assistant_response[:60] if len(h.assistant_response) > 60 else h.assistant_response
        print(f"\n{hora} | {intent:20} | 👤: {user_msg}")
        print(f"{'':7}{'':22} | 🤖: {bot_msg}")
else:
    print("❌ Nenhum histórico encontrado")

# Buscar por palavra-chave "pintura"
print("\n\n🔍 Buscando transações com 'pintura':")
print("-" * 80)
pintura = Transacao.objects.filter(casa=user.casa, titulo__icontains='pintura')
if pintura.exists():
    for t in pintura:
        print(f"{t.data} | {t.titulo} | R$ {t.valor} | {t.conta.nome}")
else:
    print("❌ Nenhuma transação com 'pintura' encontrada")

# Buscar por palavra-chave "casa"
print("\n\n🔍 Buscando transações com categoria 'casa':")
print("-" * 80)
casa = Transacao.objects.filter(casa=user.casa, categoria__nome__icontains='casa')
if casa.exists():
    for t in casa:
        print(f"{t.data} | {t.titulo} | {t.categoria.nome} | R$ {t.valor} | {t.conta.nome}")
else:
    print("❌ Nenhuma transação com categoria 'casa' encontrada")

# Buscar transações de mercado e gasolina
print("\n\n🔍 Buscando transações de 'mercado' ou 'gasolina' (últimos 30 dias):")
print("-" * 80)
inicio_mes = hoje - timedelta(days=30)
mercado_gas = Transacao.objects.filter(
    casa=user.casa,
    data__gte=inicio_mes
).filter(
    titulo__icontains='mercado'
) | Transacao.objects.filter(
    casa=user.casa,
    data__gte=inicio_mes
).filter(
    titulo__icontains='gasolina'
)
mercado_gas = mercado_gas.order_by('-data')

if mercado_gas.exists():
    for t in mercado_gas:
        print(f"{t.data} | {t.titulo} | R$ {t.valor} | {t.conta.nome}")
else:
    print("❌ Nenhuma transação de mercado/gasolina encontrada nos últimos 30 dias")

print("\n" + "=" * 80)
