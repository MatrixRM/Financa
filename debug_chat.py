"""
Script de debug para testar o chat financeiro em tempo real.
Execute: python debug_chat.py
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_despesas.settings')
django.setup()

from core.services.openai_client import OpenAIClient
from datetime import datetime
from zoneinfo import ZoneInfo
import json


def test_prompt():
    """Testa se o prompt está correto."""
    print("\n" + "="*80)
    print("TESTE 1: Verificando Prompt do Sistema")
    print("="*80)
    
    client = OpenAIClient()
    prompt = client._get_system_prompt()
    
    tz_br = ZoneInfo('America/Sao_Paulo')
    hoje = datetime.now(tz_br).strftime("%d/%m/%Y")
    
    print(f"\n📅 Data de hoje esperada: {hoje}")
    print(f"✓ Data encontrada no prompt: {'SIM' if hoje in prompt else 'NÃO ❌'}")
    print(f"✓ Contém 'edit_transaction': {'SIM' if 'edit_transaction' in prompt else 'NÃO ❌'}")
    print(f"✓ Contém 'search_criteria': {'SIM' if 'search_criteria' in prompt else 'NÃO ❌'}")
    
    print(f"\n📝 Prompt completo (primeiras 500 chars):")
    print("-"*80)
    print(prompt[:500] + "...")
    print("-"*80)


def test_message_parsing(message):
    """Testa o parsing de uma mensagem."""
    print("\n" + "="*80)
    print(f"TESTE 2: Parsing da mensagem: '{message}'")
    print("="*80)
    
    try:
        client = OpenAIClient()
        result = client.parse_user_message(message=message, context=[])
        
        print("\n✓ Resposta da IA:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Análise da resposta
        print("\n📊 Análise:")
        print(f"  - Intent: {result.get('intent')}")
        print(f"  - Clarification needed: {result.get('clarification_needed')}")
        print(f"  - Confidence: {result.get('confidence', 'N/A')}")
        
        if result.get('transaction'):
            print(f"\n💰 Dados da transação:")
            for key, value in result['transaction'].items():
                print(f"    {key}: {value}")
        
        if result.get('search_criteria'):
            print(f"\n🔍 Critérios de busca:")
            for key, value in result['search_criteria'].items():
                print(f"    {key}: {value}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_multiple_transactions():
    """Testa mensagem com múltiplas transações."""
    print("\n" + "="*80)
    print("TESTE 3: Múltiplas Transações")
    print("="*80)
    
    messages = [
        "Gastei 30 reais no café e 50 no almoço",
        "Comprei pão por 5 reais e leite por 8 reais",
        "Recebi 100 de freelance e 50 de bônus"
    ]
    
    for msg in messages:
        print(f"\n📝 Mensagem: '{msg}'")
        result = test_message_parsing(msg)
        if result and result.get('transaction'):
            print(f"  ⚠️  Sistema detectou apenas UMA transação (limitação atual)")
            print(f"  💡 Sugestão: Enviar mensagens separadas para cada transação")


def test_edit_transaction():
    """Testa edição de transação."""
    print("\n" + "="*80)
    print("TESTE 4: Edição de Transação")
    print("="*80)
    
    messages = [
        "Edite a transação de pintura para 350 reais",
        "Altere o valor do mercado para 200",
        "Mude a transação de almoço para 60 reais"
    ]
    
    for msg in messages:
        print(f"\n📝 Mensagem: '{msg}'")
        result = test_message_parsing(msg)
        
        if result:
            intent = result.get('intent')
            if intent == 'edit_transaction':
                print("  ✓ IA identificou corretamente como EDIÇÃO")
            elif intent == 'create_transaction':
                print("  ❌ IA identificou como CRIAÇÃO (deveria ser EDIÇÃO)")
            else:
                print(f"  ❌ Intent inesperado: {intent}")


def main():
    """Função principal."""
    print("\n" + "="*80)
    print("🔍 DEBUG DO CHAT FINANCEIRO")
    print("="*80)
    
    # Teste 1: Prompt
    test_prompt()
    
    # Teste 2: Mensagens simples
    print("\n\n")
    test_message_parsing("Gastei 45 reais no almoço hoje")
    
    # Teste 3: Múltiplas transações
    print("\n\n")
    test_multiple_transactions()
    
    # Teste 4: Edição
    print("\n\n")
    test_edit_transaction()
    
    print("\n" + "="*80)
    print("FIM DOS TESTES")
    print("="*80)
    print("\n💡 Próximos passos:")
    print("  1. Se a IA não está identificando corretamente, ajustar o prompt")
    print("  2. Se a transação não está sendo salva, verificar a view")
    print("  3. Executar testes automatizados: python manage.py test core.tests.test_chat")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
