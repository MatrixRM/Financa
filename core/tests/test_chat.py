"""
Testes automatizados para o sistema de chat financeiro.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import date

from core.models import Casa, Conta, Categoria, Transacao
from core.services.openai_client import OpenAIClient

User = get_user_model()


class ChatIntegrationTestCase(TestCase):
    """Testes de integração do chat financeiro."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        # Criar casa
        self.casa = Casa.objects.create(nome="Casa Teste")
        
        # Criar usuário
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.user.casa = self.casa
        self.user.save()
        
        # Criar conta padrão
        self.conta = Conta.objects.create(
            casa=self.casa,
            nome='Carteira',
            tipo='corrente',
            saldo_inicial=Decimal('1000.00')
        )
        
        # Criar categoria padrão
        self.categoria = Categoria.objects.create(
            casa=self.casa,
            nome='Alimentação',
            tipo='despesa',
            cor='#FF5733'
        )
        
        # Cliente de teste
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    @patch('core.views.OpenAIClient')
    def test_chat_criar_uma_despesa_simples(self, mock_openai):
        """Teste: Criar uma despesa simples via chat."""
        # Mock da resposta da IA
        mock_instance = mock_openai.return_value
        mock_instance.parse_user_message.return_value = {
            'intent': 'create_transaction',
            'clarification_needed': False,
            'assistant_message': 'Registrei sua despesa de R$ 45,00 no almoço.',
            'transaction': {
                'type': 'despesa',
                'amount': 45.00,
                'category': 'Alimentação',
                'account': 'Carteira',
                'date': str(date.today()),
                'title': 'Almoço',
                'notes': 'Criado via chat'
            },
            'confidence': 0.95
        }
        
        # Enviar mensagem
        response = self.client.post(
            '/chat/message/',
            data=json.dumps({
                'message': 'Gastei 45 reais no almoço hoje',
                'context': []
            }),
            content_type='application/json'
        )
        
        # Verificações
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['intent'], 'create_transaction')
        self.assertTrue(data.get('transaction_saved', False))
        
        # Verificar se a transação foi criada no banco
        transacao = Transacao.objects.filter(
            casa=self.casa,
            tipo='despesa',
            valor=Decimal('45.00')
        ).first()
        
        self.assertIsNotNone(transacao, "Transação não foi criada no banco de dados")
        self.assertEqual(transacao.categoria.nome, 'Alimentação')
        
    @patch('core.views.OpenAIClient')
    def test_chat_criar_duas_despesas_seguidas(self, mock_openai):
        """Teste: Criar duas despesas na mesma mensagem."""
        mock_instance = mock_openai.return_value
        
        # Primeira despesa
        mock_instance.parse_user_message.side_effect = [
            {
                'intent': 'create_transaction',
                'clarification_needed': False,
                'assistant_message': 'Registrei R$ 30,00 em café e R$ 50,00 em almoço.',
                'transaction': {
                    'type': 'despesa',
                    'amount': 30.00,
                    'category': 'Alimentação',
                    'account': 'Carteira',
                    'date': str(date.today()),
                    'title': 'Café',
                    'notes': ''
                },
                'confidence': 0.9
            }
        ]
        
        # Primeira mensagem
        response1 = self.client.post(
            '/chat/message/',
            data=json.dumps({
                'message': 'Gastei 30 no café e 50 no almoço',
                'context': []
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response1.status_code, 200)
        
        # Nota: O sistema atual só cria UMA transação por mensagem
        # Este teste documenta a limitação atual
        transacoes = Transacao.objects.filter(casa=self.casa).count()
        self.assertEqual(transacoes, 1, "Sistema só cria uma transação por vez (limitação conhecida)")
    
    @patch('core.views.OpenAIClient')
    def test_chat_editar_transacao_existente(self, mock_openai):
        """Teste: Editar uma transação existente."""
        # Criar transação para editar
        transacao_original = Transacao.objects.create(
            casa=self.casa,
            conta=self.conta,
            categoria=self.categoria,
            tipo='despesa',
            valor=Decimal('100.00'),
            titulo='Mercado',
            data=date.today(),
            pago_por=self.user,
            status='paga'
        )
        
        mock_instance = mock_openai.return_value
        mock_instance.parse_user_message.return_value = {
            'intent': 'edit_transaction',
            'clarification_needed': False,
            'assistant_message': 'Transação atualizada para R$ 150,00',
            'search_criteria': {
                'category': 'Alimentação',
                'date': str(date.today())
            },
            'transaction': {
                'amount': 150.00
            },
            'confidence': 0.9
        }
        
        # Enviar mensagem de edição
        response = self.client.post(
            '/chat/message/',
            data=json.dumps({
                'message': 'Edite a transação de alimentação para 150 reais',
                'context': []
            }),
            content_type='application/json'
        )
        
        # Verificações
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['intent'], 'edit_transaction')
        
        # Verificar se foi atualizada
        transacao_original.refresh_from_db()
        self.assertEqual(transacao_original.valor, Decimal('150.00'))
    
    @patch('core.views.OpenAIClient')
    def test_chat_clarification_needed(self, mock_openai):
        """Teste: IA precisa de esclarecimento."""
        mock_instance = mock_openai.return_value
        mock_instance.parse_user_message.return_value = {
            'intent': 'create_transaction',
            'clarification_needed': True,
            'assistant_message': 'Quanto você gastou?',
            'transaction': {
                'type': 'despesa',
                'category': 'Alimentação'
            },
            'confidence': 0.5
        }
        
        response = self.client.post(
            '/chat/message/',
            data=json.dumps({
                'message': 'Gastei no mercado',
                'context': []
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['clarification_needed'])
        # NÃO deve criar transação sem valor (validação amount > 0)
        self.assertFalse(data.get('transaction_saved', False))
        
    def test_chat_history_api(self):
        """Teste: API de histórico do chat."""
        from core.models import ChatHistory
        
        # Criar histórico
        ChatHistory.objects.create(
            usuario=self.user,
            user_message='Teste 1',
            assistant_response='Resposta 1',
            intent='greeting'
        )
        ChatHistory.objects.create(
            usuario=self.user,
            user_message='Teste 2',
            assistant_response='Resposta 2',
            intent='create_transaction'
        )
        
        # Buscar histórico
        response = self.client.get('/chat/history/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('messages', data)
        self.assertEqual(len(data['messages']), 4)  # 2 mensagens x 2 (user + assistant)


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
