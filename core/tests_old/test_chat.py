# Arquivo de compatibilidade: testes foram movidos para `core.tests_core`
# Este arquivo apenas importa os testes do novo pacote para manter compatibilidade.
from core.tests_core.test_chat import *


class ChatPromptTestCase(TestCase):
    """Testes específicos do prompt da IA."""
    
    def test_prompt_contem_data_atual(self):
        """Teste: Prompt contém a data atual."""
        from core.services.openai_client import OpenAIClient
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        client = OpenAIClient()
        prompt = client._get_system_prompt()
        
        # Verificar se contém data de hoje
        tz_br = ZoneInfo('America/Sao_Paulo')
        hoje = datetime.now(tz_br).strftime("%d/%m/%Y")
        self.assertIn(hoje, prompt, f"Prompt não contém data atual {hoje}")
    
    def test_prompt_contem_regras_edicao(self):
        """Teste: Prompt contém instruções de edição."""
        from core.services.openai_client import OpenAIClient
        
        client = OpenAIClient()
        prompt = client._get_system_prompt()
        
        # Verificar palavras-chave
        self.assertIn('edit_transaction', prompt)
        self.assertIn('editar', prompt.lower())
        self.assertIn('search_criteria', prompt)


class ChatFunctionsTestCase(TestCase):
    """Testes das funções auxiliares do chat."""
    
    def setUp(self):
        self.casa = Casa.objects.create(nome="Casa Teste")
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.user.casa = self.casa
        self.user.save()
        
        self.conta = Conta.objects.create(
            casa=self.casa,
            nome='Carteira',
            tipo='corrente',
            saldo_inicial=Decimal('1000.00')
        )
        
        self.categoria = Categoria.objects.create(
            casa=self.casa,
            nome='Alimentação',
            tipo='despesa'
        )
    
    def test_search_transactions_por_categoria(self):
        """Teste: Buscar transações por categoria."""
        from core.views import search_transactions
        
        # Criar transações
        Transacao.objects.create(
            casa=self.casa,
            conta=self.conta,
            categoria=self.categoria,
            tipo='despesa',
            valor=Decimal('50.00'),
            titulo='Mercado',
            data=date.today(),
            pago_por=self.user
        )
        
        # Buscar
        results = search_transactions(self.user, {'category': 'Alimentação'})
        self.assertEqual(results.count(), 1)
    
    def test_format_transaction_preview(self):
        """Teste: Formatação de preview de transação."""
        from core.views import format_transaction_preview
        
        transacao = Transacao.objects.create(
            casa=self.casa,
            conta=self.conta,
            categoria=self.categoria,
            tipo='despesa',
            valor=Decimal('100.00'),
            titulo='Teste',
            data=date.today(),
            pago_por=self.user
        )
        
        preview = format_transaction_preview(transacao)
        self.assertIn('R$ 100.00', preview)
        self.assertIn('Alimentação', preview)
        self.assertIn('💸', preview)


def run_diagnostic_tests():
    """Função para executar testes de diagnóstico e exibir resultados."""
    import sys
    from io import StringIO
    from django.test.runner import DiscoverRunner
    
    # Capturar output
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    # Executar testes
    runner = DiscoverRunner(verbosity=2)
    failures = runner.run_tests(['core.tests.test_chat'])
    
    # Restaurar stdout
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    print("\n" + "="*80)
    print("RESULTADOS DOS TESTES DE DIAGNÓSTICO DO CHAT")
    print("="*80)
    print(output)
    print("="*80)
    print(f"\nTotal de falhas: {failures}")
    print("="*80)
    
    return failures == 0
