from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal


class Usuario(AbstractUser):
    """Modelo customizado de usuário"""
    casa = models.ForeignKey('Casa', on_delete=models.CASCADE, null=True, blank=True, related_name='membros')
    telefone = models.CharField(max_length=20, blank=True)
    foto_perfil = models.ImageField(upload_to='perfis/', null=True, blank=True)
    biometria_habilitada = models.BooleanField(default=False, verbose_name='Biometria Habilitada')
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
    
    def __str__(self):
        return self.get_full_name() or self.username


class CredencialBiometrica(models.Model):
    """Armazena credenciais WebAuthn para autenticação biométrica"""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='credenciais_biometricas')
    credential_id = models.TextField(unique=True, verbose_name='ID da Credencial')
    public_key = models.TextField(verbose_name='Chave Pública')
    sign_count = models.IntegerField(default=0, verbose_name='Contador de Assinaturas')
    nome_dispositivo = models.CharField(max_length=100, blank=True, verbose_name='Nome do Dispositivo')
    criada_em = models.DateTimeField(auto_now_add=True, verbose_name='Criada em')
    ultimo_uso = models.DateTimeField(null=True, blank=True, verbose_name='Último Uso')
    ativa = models.BooleanField(default=True, verbose_name='Ativa')
    
    class Meta:
        verbose_name = 'Credencial Biométrica'
        verbose_name_plural = 'Credenciais Biométricas'
        ordering = ['-criada_em']
    
    def __str__(self):
        dispositivo = self.nome_dispositivo or 'Dispositivo'
        return f"{self.usuario.username} - {dispositivo}"


class Casa(models.Model):
    """Modelo de Casa/Família - compartilhada por até 2 pessoas"""
    nome = models.CharField(max_length=100)
    criada_em = models.DateTimeField(auto_now_add=True)
    codigo_convite = models.CharField(max_length=8, unique=True, blank=True)
    
    class Meta:
        verbose_name = 'Casa'
        verbose_name_plural = 'Casas'
    
    def __str__(self):
        return self.nome
    
    def gerar_codigo_convite(self):
        """Gera um código único de 8 caracteres para convite"""
        import random
        import string
        while True:
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Casa.objects.filter(codigo_convite=codigo).exists():
                self.codigo_convite = codigo
                self.save()
                return codigo
    
    @property
    def tem_vaga(self):
        """Verifica se ainda há vaga na casa (máximo 2 membros)"""
        return self.membros.count() < 2
    
    @property
    def saldo_total(self):
        """Calcula o saldo total de todas as contas"""
        return sum(conta.saldo_atual for conta in self.contas.all())


class Conta(models.Model):
    """Modelo de Conta Bancária"""
    TIPO_CHOICES = [
        ('conta_corrente', 'Conta Corrente'),
        ('poupanca', 'Poupança'),
        ('cartao_credito', 'Cartão de Crédito'),
        ('dinheiro', 'Dinheiro'),
        ('investimento', 'Investimento'),
        ('outro', 'Outro'),
    ]
    
    casa = models.ForeignKey(Casa, on_delete=models.CASCADE, related_name='contas')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='conta_corrente')
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0.00'))])
    cor = models.CharField(max_length=7, default='#007bff', help_text='Cor em hexadecimal')
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Conta'
        verbose_name_plural = 'Contas'
        ordering = ['-ativa', 'nome']
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"
    
    @property
    def saldo_atual(self):
        """Calcula o saldo atual da conta baseado nas transações"""
        receitas = self.transacoes.filter(tipo='receita').aggregate(
            total=models.Sum('valor'))['total'] or Decimal('0.00')
        despesas = self.transacoes.filter(tipo='despesa').aggregate(
            total=models.Sum('valor'))['total'] or Decimal('0.00')
        return self.saldo_inicial + receitas - despesas


class Categoria(models.Model):
    """Modelo de Categoria de Transação"""
    TIPO_CHOICES = [
        ('despesa', 'Despesa'),
        ('receita', 'Receita'),
    ]
    
    casa = models.ForeignKey(Casa, on_delete=models.CASCADE, related_name='categorias')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    icone = models.CharField(max_length=50, default='bi-tag', help_text='Classe do ícone Bootstrap Icons')
    cor = models.CharField(max_length=7, default='#6c757d', help_text='Cor em hexadecimal')
    ativa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['tipo', 'nome']
        unique_together = ['casa', 'nome', 'tipo']
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class Transacao(models.Model):
    """Modelo de Transação Financeira"""
    TIPO_CHOICES = [
        ('despesa', 'Despesa'),
        ('receita', 'Receita'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('paga', 'Paga'),
        ('cancelada', 'Cancelada'),
    ]
    
    casa = models.ForeignKey(Casa, on_delete=models.CASCADE, related_name='transacoes')
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='transacoes')
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='transacoes')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    data = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='paga')
    observacao = models.TextField(blank=True)
    
    # Controle de pagamento/recebimento
    pago_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='transacoes_pagas')
    dividido_entre = models.ManyToManyField(Usuario, blank=True, related_name='transacoes_compartilhadas')
    
    # Recorrência
    recorrente = models.BooleanField(default=False)
    frequencia = models.CharField(
        max_length=20,
        choices=[
            ('', 'Não recorrente'),
            ('semanal', 'Semanal'),
            ('mensal', 'Mensal'),
            ('anual', 'Anual'),
        ],
        blank=True
    )
    
    # Anexos
    comprovante = models.FileField(upload_to='comprovantes/', null=True, blank=True)
    
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        ordering = ['-data', '-criada_em']
    
    def __str__(self):
        return f"{self.titulo} - R$ {self.valor} ({self.data})"
    
    def save(self, *args, **kwargs):
        # Garantir que o tipo da transação coincide com o tipo da categoria
        self.tipo = self.categoria.tipo
        super().save(*args, **kwargs)
    
    @property
    def valor_dividido(self):
        """Retorna o valor dividido se houver divisão"""
        qtd_pessoas = self.dividido_entre.count()
        if qtd_pessoas > 0:
            return self.valor / (qtd_pessoas + 1)  # +1 para incluir quem pagou
        return self.valor


class ChatHistory(models.Model):
    """Modelo para armazenar histórico de conversas do chat financeiro."""
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='chat_history',
        verbose_name='Usuário'
    )
    user_message = models.TextField(
        verbose_name='Mensagem do Usuário',
        help_text='Mensagem enviada pelo usuário'
    )
    assistant_response = models.TextField(
        verbose_name='Resposta do Assistente',
        help_text='Resposta gerada pelo assistente'
    )
    intent = models.CharField(
        max_length=50,
        verbose_name='Intenção',
        help_text='Intenção identificada pela IA',
        blank=True,
        null=True
    )
    transcribed_text = models.TextField(
        verbose_name='Texto Transcrito',
        help_text='Texto transcrito do áudio (se aplicável)',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    
    class Meta:
        verbose_name = 'Histórico de Chat'
        verbose_name_plural = 'Histórico de Chats'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['usuario', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.usuario.username} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"

