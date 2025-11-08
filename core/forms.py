from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Row, Column, Div, HTML
from .models import Usuario, Casa, Conta, Categoria, Transacao


class RegistroForm(UserCreationForm):
    """Formulário de registro de usuário"""
    first_name = forms.CharField(max_length=150, required=True, label='Nome')
    last_name = forms.CharField(max_length=150, required=True, label='Sobrenome')
    email = forms.EmailField(required=True, label='E-mail')
    
    # Opção de criar nova casa ou entrar em uma existente
    opcao = forms.ChoiceField(
        choices=[('criar', 'Criar nova casa'), ('entrar', 'Entrar em casa existente')],
        widget=forms.RadioSelect,
        label='O que deseja fazer?',
        initial='criar'
    )
    nome_casa = forms.CharField(max_length=100, required=False, label='Nome da sua casa')
    codigo_convite = forms.CharField(max_length=8, required=False, label='Código de convite')
    
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-3'),
                Column('last_name', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('username', css_class='form-group col-md-6 mb-3'),
                Column('email', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('password1', css_class='form-group col-md-6 mb-3'),
                Column('password2', css_class='form-group col-md-6 mb-3'),
            ),
            HTML('<hr>'),
            'opcao',
            'nome_casa',
            'codigo_convite',
            Div(
                Submit('submit', 'Cadastrar', css_class='btn btn-primary btn-block w-100'),
                css_class='d-grid gap-2 mt-3'
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        opcao = cleaned_data.get('opcao')
        nome_casa = cleaned_data.get('nome_casa')
        codigo_convite = cleaned_data.get('codigo_convite')
        
        if opcao == 'criar' and not nome_casa:
            raise forms.ValidationError('Por favor, informe o nome da casa.')
        
        if opcao == 'entrar':
            if not codigo_convite:
                raise forms.ValidationError('Por favor, informe o código de convite.')
            try:
                casa = Casa.objects.get(codigo_convite=codigo_convite)
                if not casa.tem_vaga:
                    raise forms.ValidationError('Esta casa já está cheia (máximo 2 membros).')
            except Casa.DoesNotExist:
                raise forms.ValidationError('Código de convite inválido.')
        
        return cleaned_data


class LoginForm(AuthenticationForm):
    """Formulário de login"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('username', placeholder='Usuário', css_class='form-control-lg'),
            Field('password', placeholder='Senha', css_class='form-control-lg'),
            Div(
                Submit('submit', 'Entrar', css_class='btn btn-primary btn-lg w-100 mt-3'),
                css_class='d-grid gap-2'
            )
        )


class ContaForm(forms.ModelForm):
    """Formulário para Conta"""
    class Meta:
        model = Conta
        fields = ['nome', 'tipo', 'saldo_inicial', 'cor', 'ativa']
        widgets = {
            'cor': forms.TextInput(attrs={'type': 'color'}),
        }
        labels = {
            'nome': 'Nome da Conta',
            'tipo': 'Tipo',
            'saldo_inicial': 'Saldo Inicial (R$)',
            'cor': 'Cor de Identificação',
            'ativa': 'Conta Ativa?',
        }
        help_texts = {
            'nome': 'Ex: Carteira, Banco XYZ, Poupança',
            'saldo_inicial': 'Saldo disponível no momento da criação da conta.',
            'cor': 'Escolha uma cor para identificar facilmente esta conta.',
        }
    
    def __init__(self, *args, **kwargs):
        self.casa = kwargs.pop('casa', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = True
        self.helper.layout = Layout(
            'nome',
            Row(
                Column('tipo', css_class='form-group col-md-6 mb-3'),
                Column('saldo_inicial', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('cor', css_class='form-group col-md-6 mb-3'),
                Column('ativa', css_class='form-group col-md-6 mb-3'),
            ),
            Div(
                Submit('submit', 'Salvar', css_class='btn btn-primary'),
                HTML('<a href="/contas/" class="btn btn-secondary">Cancelar</a>'),
                css_class='d-flex gap-2'
            )
        )
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.casa:
            instance.casa = self.casa
        if commit:
            instance.save()
        return instance


class CategoriaForm(forms.ModelForm):
    """Formulário para Categoria"""
    class Meta:
        model = Categoria
        fields = ['nome', 'tipo', 'icone', 'cor', 'ativa']
        widgets = {
            'cor': forms.TextInput(attrs={'type': 'color'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'icone': forms.HiddenInput(attrs={'class': 'form-control'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nome': 'Nome da Categoria',
            'tipo': 'Tipo',
            'icone': 'Ícone',
            'cor': 'Cor de Identificação',
            'ativa': 'Categoria Ativa?',
        }
        help_texts = {
            'nome': 'Ex: Alimentação, Transporte, Salário',
            'icone': 'Código do ícone Bootstrap (ex: bi-cart, bi-house)',
            'cor': 'Escolha uma cor para identificar facilmente esta categoria.',
        }
    
    def __init__(self, *args, **kwargs):
        self.casa = kwargs.pop('casa', None)
        super().__init__(*args, **kwargs)
        # Não usar FormHelper para ter controle total no template
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.casa:
            instance.casa = self.casa
        if commit:
            instance.save()
        return instance


class TransacaoForm(forms.ModelForm):
    """Formulário para Transação"""
    
    # Campo personalizado com autocomplete
    titulo = forms.CharField(
        max_length=200,
        label='Descrição',
        widget=forms.TextInput(attrs={
            'list': 'titulos-anteriores',
            'placeholder': 'Ex: Supermercado, Gasolina, Aluguel...',
            'autocomplete': 'off',
            'class': 'form-control'
        }),
        help_text='Digite ou escolha uma descrição já utilizada'
    )
    
    class Meta:
        model = Transacao
        fields = [
            'titulo', 'valor', 'data', 'categoria', 'conta', 'status',
            'observacao', 'dividido_entre', 'recorrente', 'frequencia', 'comprovante'
        ]
        widgets = {
            'data': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'valor': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0,00',
                'class': 'form-control'
            }),
            'observacao': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Adicione detalhes sobre esta transação...'
            }),
            'dividido_entre': forms.CheckboxSelectMultiple(),
        }
        labels = {
            'titulo': 'Descrição',
            'valor': 'Valor (R$)',
            'data': 'Data',
            'categoria': 'Categoria',
            'conta': 'Conta',
            'status': 'Status',
            'observacao': 'Observações',
            'dividido_entre': 'Dividir com',
            'recorrente': 'Recorrente?',
            'frequencia': 'Frequência',
            'comprovante': 'Comprovante (opcional)',
        }
        help_texts = {
            'valor': 'Digite o valor em reais (ex: 50,00 ou 50.00)',
            'dividido_entre': 'Selecione os membros da casa para dividir esta transação.',
            'recorrente': 'Marque se esta transação se repete regularmente.',
            'comprovante': 'Anexe um arquivo PDF, imagem ou outro documento.',
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        self.casa = kwargs.pop('casa', None)
        tipo_transacao = kwargs.pop('tipo', None)
        super().__init__(*args, **kwargs)
        
        # Definir data padrão como hoje se for um novo formulário
        if not self.instance.pk:
            from datetime import date
            self.initial['data'] = date.today()
            self.initial['status'] = 'paga'
        
        # Filtrar categorias e contas pela casa
        if self.casa:
            self.fields['categoria'].queryset = Categoria.objects.filter(casa=self.casa, ativa=True).order_by('nome')
            self.fields['conta'].queryset = Conta.objects.filter(casa=self.casa, ativa=True).order_by('nome')
            self.fields['dividido_entre'].queryset = Usuario.objects.filter(casa=self.casa)
            
            # Filtrar por tipo se fornecido
            if tipo_transacao:
                self.fields['categoria'].queryset = self.fields['categoria'].queryset.filter(tipo=tipo_transacao)
        
        # Personalizar labels das categorias com ícones
        self.fields['categoria'].label_from_instance = lambda obj: f"{obj.nome}"
        
        # Campos opcionais para melhor UX
        self.fields['observacao'].required = False
        self.fields['comprovante'].required = False
        self.fields['recorrente'].required = False
        self.fields['frequencia'].required = False
        
        # Ocultar campo "dividido_entre" por padrão (pode ser expandido)
        self.fields['dividido_entre'].required = False
        self.fields['dividido_entre'].help_text = 'Marque para dividir o valor com outros membros'
        
        # Layout do formulário
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.form_tag = True
        
        # Layout inteligente baseado no tipo
        if tipo_transacao == 'receita':
            # Para receitas: campos simplificados (sem status, sem divisão)
            self.helper.layout = Layout(
                HTML('<input type="hidden" name="tipo" value="{{ tipo }}">'),
                HTML('<input type="hidden" name="status" value="paga">'),  # Receita sempre "paga"
                HTML('''
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <i class="bi bi-lightbulb"></i> 
                        <strong>Dica:</strong> Para receitas, apenas informe o essencial: descrição, valor, data e categoria.
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                '''),
                'titulo',
                Row(
                    Column('valor', css_class='form-group col-md-6 mb-3'),
                    Column('data', css_class='form-group col-md-6 mb-3'),
                ),
                Row(
                    Column('categoria', css_class='form-group col-md-6 mb-3'),
                    Column('conta', css_class='form-group col-md-6 mb-3'),
                ),
                HTML('''
                    <div class="mb-3">
                        <button type="button" class="btn btn-link p-0" data-bs-toggle="collapse" data-bs-target="#opcoesAvancadas">
                            <i class="bi bi-chevron-down"></i> Mostrar opções avançadas
                        </button>
                    </div>
                '''),
                HTML('<div class="collapse" id="opcoesAvancadas">'),
                'observacao',
                Row(
                    Column('recorrente', css_class='form-group col-md-6 mb-3'),
                    Column('frequencia', css_class='form-group col-md-6 mb-3'),
                ),
                'comprovante',
                HTML('</div>'),
                HTML('<hr>'),
                Div(
                    Submit('submit', 'Salvar Receita', css_class='btn btn-success btn-lg'),
                    HTML('<a href="/transacoes/" class="btn btn-secondary btn-lg">Cancelar</a>'),
                    css_class='d-flex gap-2 mt-3'
                )
            )
        else:
            # Para despesas: campos completos mas organizados
            self.helper.layout = Layout(
                HTML('<input type="hidden" name="tipo" value="{{ tipo }}">'),
                HTML('''
                    <div class="alert alert-info alert-dismissible fade show" role="alert">
                        <i class="bi bi-lightbulb"></i> 
                        <strong>Dica:</strong> Comece digitando a descrição para ver sugestões de despesas anteriores.
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                '''),
                'titulo',
                Row(
                    Column('valor', css_class='form-group col-md-4 mb-3'),
                    Column('data', css_class='form-group col-md-4 mb-3'),
                    Column('status', css_class='form-group col-md-4 mb-3'),
                ),
                Row(
                    Column('categoria', css_class='form-group col-md-6 mb-3'),
                    Column('conta', css_class='form-group col-md-6 mb-3'),
                ),
                HTML('''
                    <div class="mb-3">
                        <button type="button" class="btn btn-link p-0" data-bs-toggle="collapse" data-bs-target="#opcoesAvancadas">
                            <i class="bi bi-chevron-down"></i> Mostrar opções avançadas
                        </button>
                    </div>
                '''),
                HTML('<div class="collapse" id="opcoesAvancadas">'),
                HTML('<h6 class="mb-3"><i class="bi bi-sliders"></i> Opções Avançadas</h6>'),
                'observacao',
                'dividido_entre',
                Row(
                    Column('recorrente', css_class='form-group col-md-6 mb-3'),
                    Column('frequencia', css_class='form-group col-md-6 mb-3'),
                ),
                'comprovante',
                HTML('</div>'),
                HTML('<hr>'),
                Div(
                    Submit('submit', 'Salvar Despesa', css_class='btn btn-danger btn-lg'),
                    HTML('<a href="/transacoes/" class="btn btn-secondary btn-lg">Cancelar</a>'),
                    css_class='d-flex gap-2 mt-3'
                )
            )
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.casa:
            instance.casa = self.casa
        if self.usuario:
            instance.pago_por = self.usuario
        if commit:
            instance.save()
            self.save_m2m()  # Salvar relações many-to-many
        return instance


class FiltroTransacaoForm(forms.Form):
    """Formulário de filtros para transações"""
    data_inicio = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label='Data Início')
    data_fim = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label='Data Fim')
    tipo = forms.ChoiceField(
        choices=[('', 'Todos')] + Transacao.TIPO_CHOICES,
        required=False,
        label='Tipo'
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        required=False,
        label='Categoria'
    )
    conta = forms.ModelChoiceField(
        queryset=Conta.objects.none(),
        required=False,
        label='Conta'
    )
    status = forms.ChoiceField(
        choices=[('', 'Todos')] + Transacao.STATUS_CHOICES,
        required=False,
        label='Status'
    )
    
    def __init__(self, *args, **kwargs):
        casa = kwargs.pop('casa', None)
        super().__init__(*args, **kwargs)
        
        if casa:
            self.fields['categoria'].queryset = Categoria.objects.filter(casa=casa)
            self.fields['conta'].queryset = Conta.objects.filter(casa=casa)
        
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'form-inline'
        self.helper.layout = Layout(
            Row(
                Column('data_inicio', css_class='form-group col-md-2 mb-2'),
                Column('data_fim', css_class='form-group col-md-2 mb-2'),
                Column('tipo', css_class='form-group col-md-2 mb-2'),
                Column('categoria', css_class='form-group col-md-2 mb-2'),
                Column('conta', css_class='form-group col-md-2 mb-2'),
                Column('status', css_class='form-group col-md-2 mb-2'),
            ),
            Div(
                Submit('filtrar', 'Filtrar', css_class='btn btn-primary'),
                HTML('<a href="{% url \'transacao_list\' %}" class="btn btn-secondary">Limpar</a>'),
                css_class='d-flex gap-2'
            )
        )
