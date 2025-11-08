from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random

from core.models import Usuario, Casa, Conta, Categoria, Transacao


class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de exemplo'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando população do banco de dados...'))

        # Criar Casa
        casa, created = Casa.objects.get_or_create(
            nome='Casa da Família Silva',
            defaults={'codigo_convite': 'DEMO2025'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Casa criada: {casa.nome}'))
            self.stdout.write(self.style.WARNING(f'Código de convite: {casa.codigo_convite}'))

        # Criar Usuários
        usuario1, created = Usuario.objects.get_or_create(
            username='joao',
            defaults={
                'first_name': 'João',
                'last_name': 'Silva',
                'email': 'joao@email.com',
                'casa': casa
            }
        )
        if created:
            usuario1.set_password('senha123')
            usuario1.save()
            self.stdout.write(self.style.SUCCESS(f'Usuário criado: {usuario1.username}'))

        usuario2, created = Usuario.objects.get_or_create(
            username='maria',
            defaults={
                'first_name': 'Maria',
                'last_name': 'Silva',
                'email': 'maria@email.com',
                'casa': casa
            }
        )
        if created:
            usuario2.set_password('senha123')
            usuario2.save()
            self.stdout.write(self.style.SUCCESS(f'Usuário criado: {usuario2.username}'))

        # Criar Contas
        contas_data = [
            {'nome': 'Conta Corrente', 'tipo': 'conta_corrente', 'saldo_inicial': Decimal('5000.00'), 'cor': '#0d6efd'},
            {'nome': 'Poupança', 'tipo': 'poupanca', 'saldo_inicial': Decimal('10000.00'), 'cor': '#198754'},
            {'nome': 'Cartão de Crédito', 'tipo': 'cartao_credito', 'saldo_inicial': Decimal('0.00'), 'cor': '#dc3545'},
            {'nome': 'Dinheiro', 'tipo': 'dinheiro', 'saldo_inicial': Decimal('500.00'), 'cor': '#ffc107'},
        ]

        contas = []
        for conta_data in contas_data:
            conta, created = Conta.objects.get_or_create(
                casa=casa,
                nome=conta_data['nome'],
                defaults={
                    'tipo': conta_data['tipo'],
                    'saldo_inicial': conta_data['saldo_inicial'],
                    'cor': conta_data['cor']
                }
            )
            contas.append(conta)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Conta criada: {conta.nome}'))

        # Criar Categorias de Despesas
        categorias_despesas = [
            {'nome': 'Alimentação', 'icone': 'bi-cart', 'cor': '#ff6b6b'},
            {'nome': 'Transporte', 'icone': 'bi-car-front', 'cor': '#4ecdc4'},
            {'nome': 'Moradia', 'icone': 'bi-house', 'cor': '#45b7d1'},
            {'nome': 'Saúde', 'icone': 'bi-heart-pulse', 'cor': '#96ceb4'},
            {'nome': 'Educação', 'icone': 'bi-book', 'cor': '#ffeaa7'},
            {'nome': 'Lazer', 'icone': 'bi-controller', 'cor': '#dfe6e9'},
            {'nome': 'Vestuário', 'icone': 'bi-bag', 'cor': '#a29bfe'},
            {'nome': 'Telefone/Internet', 'icone': 'bi-phone', 'cor': '#fd79a8'},
            {'nome': 'Outros', 'icone': 'bi-three-dots', 'cor': '#636e72'},
        ]

        categorias_desp = []
        for cat_data in categorias_despesas:
            cat, created = Categoria.objects.get_or_create(
                casa=casa,
                nome=cat_data['nome'],
                tipo='despesa',
                defaults={
                    'icone': cat_data['icone'],
                    'cor': cat_data['cor']
                }
            )
            categorias_desp.append(cat)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Categoria criada: {cat.nome} (Despesa)'))

        # Criar Categorias de Receitas
        categorias_receitas = [
            {'nome': 'Salário', 'icone': 'bi-cash-stack', 'cor': '#00b894'},
            {'nome': 'Freelance', 'icone': 'bi-laptop', 'cor': '#00cec9'},
            {'nome': 'Investimentos', 'icone': 'bi-graph-up-arrow', 'cor': '#0984e3'},
            {'nome': 'Outras Receitas', 'icone': 'bi-plus-circle', 'cor': '#6c5ce7'},
        ]

        categorias_rec = []
        for cat_data in categorias_receitas:
            cat, created = Categoria.objects.get_or_create(
                casa=casa,
                nome=cat_data['nome'],
                tipo='receita',
                defaults={
                    'icone': cat_data['icone'],
                    'cor': cat_data['cor']
                }
            )
            categorias_rec.append(cat)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Categoria criada: {cat.nome} (Receita)'))

        # Criar Transações de exemplo (últimos 3 meses)
        hoje = timezone.now().date()
        
        # Receitas
        receitas_exemplo = [
            {'titulo': 'Salário João', 'valor': Decimal('5000.00'), 'categoria': categorias_rec[0], 'usuario': usuario1, 'conta': contas[0]},
            {'titulo': 'Salário Maria', 'valor': Decimal('4500.00'), 'categoria': categorias_rec[0], 'usuario': usuario2, 'conta': contas[0]},
            {'titulo': 'Freelance Design', 'valor': Decimal('800.00'), 'categoria': categorias_rec[1], 'usuario': usuario2, 'conta': contas[0]},
        ]

        for mes in range(3):
            data_base = hoje - timedelta(days=30 * mes)
            for rec in receitas_exemplo:
                transacao, created = Transacao.objects.get_or_create(
                    casa=casa,
                    titulo=rec['titulo'],
                    data=data_base.replace(day=5),
                    defaults={
                        'valor': rec['valor'],
                        'categoria': rec['categoria'],
                        'conta': rec['conta'],
                        'tipo': 'receita',
                        'pago_por': rec['usuario'],
                        'status': 'paga'
                    }
                )

        # Despesas variadas
        despesas_exemplo = [
            {'titulo': 'Supermercado', 'valor_min': 200, 'valor_max': 600, 'categoria': categorias_desp[0]},
            {'titulo': 'Gasolina', 'valor_min': 150, 'valor_max': 300, 'categoria': categorias_desp[1]},
            {'titulo': 'Aluguel', 'valor_min': 1200, 'valor_max': 1200, 'categoria': categorias_desp[2]},
            {'titulo': 'Conta de Luz', 'valor_min': 150, 'valor_max': 250, 'categoria': categorias_desp[2]},
            {'titulo': 'Internet', 'valor_min': 100, 'valor_max': 100, 'categoria': categorias_desp[7]},
            {'titulo': 'Academia', 'valor_min': 80, 'valor_max': 80, 'categoria': categorias_desp[3]},
            {'titulo': 'Netflix', 'valor_min': 45, 'valor_max': 45, 'categoria': categorias_desp[5]},
            {'titulo': 'Restaurante', 'valor_min': 80, 'valor_max': 200, 'categoria': categorias_desp[0]},
            {'titulo': 'Farmácia', 'valor_min': 50, 'valor_max': 150, 'categoria': categorias_desp[3]},
        ]

        transacoes_criadas = 0
        for mes in range(3):
            for dia in range(1, 31, random.randint(2, 5)):
                desp = random.choice(despesas_exemplo)
                data_transacao = hoje - timedelta(days=30 * mes + (30 - dia))
                
                if data_transacao <= hoje:
                    valor = Decimal(str(random.uniform(desp['valor_min'], desp['valor_max'])))
                    usuario = random.choice([usuario1, usuario2])
                    conta = random.choice(contas)
                    
                    transacao, created = Transacao.objects.get_or_create(
                        casa=casa,
                        titulo=desp['titulo'],
                        data=data_transacao,
                        categoria=desp['categoria'],
                        defaults={
                            'valor': valor,
                            'conta': conta,
                            'tipo': 'despesa',
                            'pago_por': usuario,
                            'status': 'paga'
                        }
                    )
                    if created:
                        transacoes_criadas += 1

        self.stdout.write(self.style.SUCCESS(f'{transacoes_criadas} transações criadas!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Banco de dados populado com sucesso!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.WARNING('Credenciais de acesso:'))
        self.stdout.write(self.style.WARNING(f'Usuário 1: joao / senha123'))
        self.stdout.write(self.style.WARNING(f'Usuário 2: maria / senha123'))
        self.stdout.write(self.style.WARNING(f'Código da casa: {casa.codigo_convite}'))
