
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import logging
import os
import base64
import json
from reportlab.lib.pagesizes import letter, A4

# Importar views de chat do módulo separado
from .chat_views.chat_views import (
    chat_interface_view,
    chat_message_view,
    chat_history_view
)
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# Django REST Framework imports
from rest_framework import status as rest_status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from .models import Usuario, Casa, Conta, Categoria, Transacao
from .forms import (
    RegistroForm, LoginForm, ContaForm, CategoriaForm,
    TransacaoForm, FiltroTransacaoForm
)
from core.serializers.chat_serializers import ChatMessageSerializer, ChatResponseSerializer
from core.services.openai_client import OpenAIClient, OpenAIClientError

# Configurar logger
logger = logging.getLogger(__name__)
logger_chat = logging.getLogger(__name__)


# ===========================
# Views de Autenticação
# ===========================

def registro_view(request):
    """View de registro de novo usuário"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            opcao = form.cleaned_data['opcao']
            user = form.save(commit=False)
            
            if opcao == 'criar':
                # Criar nova casa
                nome_casa = form.cleaned_data['nome_casa']
                casa = Casa.objects.create(nome=nome_casa)
                casa.gerar_codigo_convite()
                user.casa = casa
                user.save()
                messages.success(request, f'Casa "{nome_casa}" criada com sucesso! Código de convite: {casa.codigo_convite}')
            else:
                # Entrar em casa existente
                codigo_convite = form.cleaned_data['codigo_convite']
                casa = Casa.objects.get(codigo_convite=codigo_convite)
                user.casa = casa
                user.save()
                messages.success(request, f'Você entrou na casa "{casa.nome}" com sucesso!')
            
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegistroForm()
    
    return render(request, 'auth/registro.html', {'form': form})


def login_view(request):
    """View de login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.get_full_name() or user.username}!')
            return redirect('dashboard')
    else:
        form = LoginForm()
    
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """View de logout"""
    logout(request)
    messages.info(request, 'Você saiu do sistema.')
    return redirect('login')


@login_required
def perfil_view(request):
    """View de perfil do usuário"""
    # Se o usuário não tem casa, permitir criar ou entrar em uma
    if request.method == 'POST' and not request.user.casa:
        opcao = request.POST.get('opcao')
        
        if opcao == 'criar':
            nome_casa = request.POST.get('nome_casa')
            if nome_casa:
                casa = Casa.objects.create(nome=nome_casa)
                casa.gerar_codigo_convite()
                request.user.casa = casa
                request.user.save()
                messages.success(request, f'Casa "{nome_casa}" criada com sucesso! Código de convite: {casa.codigo_convite}')
                return redirect('dashboard')
            else:
                messages.error(request, 'Por favor, informe o nome da casa.')
        
        elif opcao == 'entrar':
            codigo_convite = request.POST.get('codigo_convite')
            if codigo_convite:
                try:
                    casa = Casa.objects.get(codigo_convite=codigo_convite.upper())
                    if not casa.tem_vaga:
                        messages.error(request, 'Esta casa já está cheia (máximo 2 membros).')
                    else:
                        request.user.casa = casa
                        request.user.save()
                        messages.success(request, f'Você entrou na casa "{casa.nome}" com sucesso!')
                        return redirect('dashboard')
                except Casa.DoesNotExist:
                    messages.error(request, 'Código de convite inválido.')
            else:
                messages.error(request, 'Por favor, informe o código de convite.')
    
    return render(request, 'auth/perfil.html')


@login_required
def casa_detalhes_view(request):
    """View de detalhes da casa"""
    casa = request.user.casa
    if not casa:
        messages.warning(request, 'Você não está associado a nenhuma casa.')
        return redirect('dashboard')
    
    return render(request, 'auth/casa_detalhes.html', {'casa': casa})


# ===========================
# Dashboard
# ===========================

@login_required
def dashboard_view(request):
    """View principal - Dashboard"""
    casa = request.user.casa
    if not casa:
        messages.warning(request, 'Você precisa estar associado a uma casa para usar o sistema.')
        return redirect('perfil')
    
    # Obter mês atual
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    
    # Estatísticas gerais
    total_receitas = Transacao.objects.filter(
        casa=casa,
        tipo='receita',
        status='paga'
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    total_despesas = Transacao.objects.filter(
        casa=casa,
        tipo='despesa',
        status='paga'
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    saldo_total = casa.saldo_total
    
    # Transações do mês
    receitas_mes = Transacao.objects.filter(
        casa=casa,
        tipo='receita',
        data__gte=primeiro_dia_mes,
        status='paga'
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    despesas_mes = Transacao.objects.filter(
        casa=casa,
        tipo='despesa',
        data__gte=primeiro_dia_mes,
        status='paga'
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    # Últimas transações
    transacoes_recentes = Transacao.objects.filter(casa=casa).order_by('-data', '-criada_em')[:10]
    
    # Contas
    contas = Conta.objects.filter(casa=casa, ativa=True)
    
    # Despesas por categoria (para gráfico)
    despesas_por_categoria = Transacao.objects.filter(
        casa=casa,
        tipo='despesa',
        data__gte=primeiro_dia_mes,
        status='paga'
    ).values('categoria__nome', 'categoria__cor').annotate(
        total=Sum('valor')
    ).order_by('-total')[:10]
    
    context = {
        'casa': casa,
        'total_receitas': total_receitas,
        'total_despesas': total_despesas,
        'saldo_total': saldo_total,
        'receitas_mes': receitas_mes,
        'despesas_mes': despesas_mes,
        'saldo_mes': receitas_mes - despesas_mes,
        'transacoes_recentes': transacoes_recentes,
        'contas': contas,
        'despesas_por_categoria': despesas_por_categoria,
    }
    
    return render(request, 'dashboard.html', context)


# ===========================
# CRUD de Contas
# ===========================

@login_required
def conta_list_view(request):
    """Lista de contas"""
    casa = request.user.casa
    if not casa:
        messages.warning(request, 'Você precisa estar associado a uma casa.')
        return redirect('dashboard')
    
    contas = Conta.objects.filter(casa=casa).order_by('-ativa', 'nome')
    
    return render(request, 'accounts/conta_list.html', {'contas': contas})


@login_required
def conta_create_view(request):
    """Criar nova conta"""
    casa = request.user.casa
    if not casa:
        messages.warning(request, 'Você precisa estar associado a uma casa.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ContaForm(request.POST, casa=casa)
        if form.is_valid():
            conta = form.save()
            messages.success(request, f'Conta "{conta.nome}" criada com sucesso!')
            return redirect('conta_list')
    else:
        form = ContaForm(casa=casa)
    
    return render(request, 'accounts/conta_form.html', {'form': form, 'title': 'Nova Conta'})


@login_required
def conta_update_view(request, pk):
    """Atualizar conta"""
    casa = request.user.casa
    conta = get_object_or_404(Conta, pk=pk, casa=casa)
    
    if request.method == 'POST':
        form = ContaForm(request.POST, instance=conta, casa=casa)
        if form.is_valid():
            conta = form.save()
            messages.success(request, f'Conta "{conta.nome}" atualizada com sucesso!')
            return redirect('conta_list')
    else:
        form = ContaForm(instance=conta, casa=casa)
    
    return render(request, 'accounts/conta_form.html', {
        'form': form,
        'title': 'Editar Conta',
        'conta': conta
    })


@login_required
def conta_delete_view(request, pk):
    """Deletar conta com opção de reatribuir transações"""
    from django.db.models import ProtectedError
    
    casa = request.user.casa
    if not casa:
        messages.error(request, 'Você não está associado a uma casa.')
        return redirect('conta_list')
    
    conta = get_object_or_404(Conta, pk=pk, casa=casa)
    
    # Verificar se há transações vinculadas
    transacoes_vinculadas = conta.transacoes.all()
    qtd_transacoes = transacoes_vinculadas.count()
    
    # Buscar outras contas disponíveis para reatribuição
    outras_contas = Conta.objects.filter(casa=casa, ativa=True).exclude(pk=pk)
    
    if request.method == 'POST':
        nome = conta.nome
        conta_id = conta.id
        
        # Verificar se usuário escolheu reatribuir transações
        reatribuir = request.POST.get('reatribuir') == 'sim'
        nova_conta_id = request.POST.get('nova_conta')
        
        try:
            if reatribuir and nova_conta_id:
                # Reatribuir todas as transações para a nova conta
                nova_conta = get_object_or_404(Conta, pk=nova_conta_id, casa=casa)
                qtd_reatribuidas = transacoes_vinculadas.update(conta=nova_conta)
                
                logger.info(
                    f"Usuário {request.user.username} reatribuiu {qtd_reatribuidas} "
                    f"transações da conta ID {conta_id} para conta ID {nova_conta_id}"
                )
                
                messages.info(
                    request,
                    f'{qtd_reatribuidas} transação(ões) foram reatribuídas para "{nova_conta.nome}"'
                )
            
            # Tentar excluir a conta
            logger.info(f"Usuário {request.user.username} tentando excluir conta ID {conta_id}: {nome}")
            conta.delete()
            logger.info(f"Conta ID {conta_id} excluída com sucesso")
            messages.success(request, f'Conta "{nome}" excluída com sucesso!')
            
        except ProtectedError as e:
            logger.error(f"Erro ProtectedError ao excluir conta ID {conta_id}: {e}")
            messages.error(
                request,
                f'Não é possível excluir a conta "{nome}" porque ela possui {qtd_transacoes} '
                f'transação(ões) vinculada(s). Reatribua as transações para outra conta primeiro.'
            )
            # Redirecionar de volta para a página de confirmação
            return render(request, 'accounts/conta_confirm_delete.html', {
                'conta': conta,
                'qtd_transacoes': qtd_transacoes,
                'outras_contas': outras_contas,
                'show_error': True
            })
            
        except Exception as e:
            logger.error(f"Erro ao excluir conta ID {conta_id}: {type(e).__name__}: {e}")
            messages.error(request, f'Erro ao excluir conta: {str(e)}')
        
        return redirect('conta_list')
    
    # GET - mostrar página de confirmação
    return render(request, 'accounts/conta_confirm_delete.html', {
        'conta': conta,
        'qtd_transacoes': qtd_transacoes,
        'outras_contas': outras_contas
    })


# ===========================
# CRUD de Categorias
# ===========================

@login_required
def categoria_list_view(request):
    """Lista de categorias"""
    casa = request.user.casa
    if not casa:
        messages.warning(request, 'Você precisa estar associado a uma casa.')
        return redirect('dashboard')
    
    categorias = Categoria.objects.filter(casa=casa).order_by('tipo', 'nome')
    
    return render(request, 'categories/categoria_list.html', {'categorias': categorias})


@login_required
def categoria_create_view(request):
    """Criar nova categoria"""
    casa = request.user.casa
    if not casa:
        messages.warning(request, 'Você precisa estar associado a uma casa.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CategoriaForm(request.POST, casa=casa)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f'Categoria "{categoria.nome}" criada com sucesso!')
            return redirect('categoria_list')
    else:
        form = CategoriaForm(casa=casa)
    
    return render(request, 'categories/categoria_form.html', {'form': form, 'title': 'Nova Categoria'})


@login_required
def categoria_update_view(request, pk):
    """Atualizar categoria"""
    casa = request.user.casa
    categoria = get_object_or_404(Categoria, pk=pk, casa=casa)
    
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria, casa=casa)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f'Categoria "{categoria.nome}" atualizada com sucesso!')
            return redirect('categoria_list')
    else:
        form = CategoriaForm(instance=categoria, casa=casa)
    
    return render(request, 'categories/categoria_form.html', {
        'form': form,
        'title': 'Editar Categoria',
        'categoria': categoria
    })


@login_required
def categoria_delete_view(request, pk):
    """Deletar categoria com opção de reatribuir transações"""
    from django.db.models import ProtectedError
    
    casa = request.user.casa
    if not casa:
        messages.error(request, 'Você não está associado a uma casa.')
        return redirect('categoria_list')
    
    categoria = get_object_or_404(Categoria, pk=pk, casa=casa)
    
    # Verificar se há transações vinculadas
    transacoes_vinculadas = categoria.transacoes.all()
    qtd_transacoes = transacoes_vinculadas.count()
    
    # Buscar outras categorias disponíveis para reatribuição (do mesmo tipo)
    outras_categorias = Categoria.objects.filter(
        casa=casa, 
        tipo=categoria.tipo, 
        ativa=True
    ).exclude(pk=pk)
    
    if request.method == 'POST':
        nome = categoria.nome
        categoria_id = categoria.id
        
        # Verificar se usuário escolheu reatribuir transações
        reatribuir = request.POST.get('reatribuir') == 'sim'
        nova_categoria_id = request.POST.get('nova_categoria')
        
        try:
            if reatribuir and nova_categoria_id:
                # Reatribuir todas as transações para a nova categoria
                nova_categoria = get_object_or_404(Categoria, pk=nova_categoria_id, casa=casa)
                qtd_reatribuidas = transacoes_vinculadas.update(categoria=nova_categoria)
                
                logger.info(
                    f"Usuário {request.user.username} reatribuiu {qtd_reatribuidas} "
                    f"transações da categoria ID {categoria_id} para categoria ID {nova_categoria_id}"
                )
                
                messages.info(
                    request,
                    f'{qtd_reatribuidas} transação(ões) foram reatribuídas para "{nova_categoria.nome}"'
                )
            
            # Tentar excluir a categoria
            logger.info(f"Usuário {request.user.username} tentando excluir categoria ID {categoria_id}: {nome}")
            categoria.delete()
            logger.info(f"Categoria ID {categoria_id} excluída com sucesso")
            messages.success(request, f'Categoria "{nome}" excluída com sucesso!')
            
        except ProtectedError as e:
            logger.error(f"Erro ProtectedError ao excluir categoria ID {categoria_id}: {e}")
            messages.error(
                request,
                f'Não é possível excluir a categoria "{nome}" porque ela possui {qtd_transacoes} '
                f'transação(ões) vinculada(s). Reatribua as transações para outra categoria primeiro.'
            )
            # Redirecionar de volta para a página de confirmação
            return render(request, 'categories/categoria_confirm_delete.html', {
                'categoria': categoria,
                'qtd_transacoes': qtd_transacoes,
                'outras_categorias': outras_categorias,
                'show_error': True
            })
            
        except Exception as e:
            logger.error(f"Erro ao excluir categoria ID {categoria_id}: {type(e).__name__}: {e}")
            messages.error(request, f'Erro ao excluir categoria: {str(e)}')
        
        return redirect('categoria_list')
    
    # GET - mostrar página de confirmação
    return render(request, 'categories/categoria_confirm_delete.html', {
        'categoria': categoria,
        'qtd_transacoes': qtd_transacoes,
        'outras_categorias': outras_categorias
    })


# ===========================
# CRUD de Transações
# ===========================

@login_required
def transacao_list_view(request):
    """Lista de transações com filtros"""
    casa = request.user.casa
    if not casa:
        messages.warning(request, 'Você precisa estar associado a uma casa.')
        return redirect('dashboard')
    
    transacoes = Transacao.objects.filter(casa=casa).select_related(
        'categoria', 'conta', 'pago_por'
    ).order_by('-data', '-criada_em')
    
    # Aplicar filtros
    filtro_form = FiltroTransacaoForm(request.GET, casa=casa)
    
    if filtro_form.is_valid():
        data_inicio = filtro_form.cleaned_data.get('data_inicio')
        data_fim = filtro_form.cleaned_data.get('data_fim')
        tipo = filtro_form.cleaned_data.get('tipo')
        categoria = filtro_form.cleaned_data.get('categoria')
        conta = filtro_form.cleaned_data.get('conta')
        status = filtro_form.cleaned_data.get('status')
        
        if data_inicio:
            transacoes = transacoes.filter(data__gte=data_inicio)
        if data_fim:
            transacoes = transacoes.filter(data__lte=data_fim)
        if tipo:
            transacoes = transacoes.filter(tipo=tipo)
        if categoria:
            transacoes = transacoes.filter(categoria=categoria)
        if conta:
            transacoes = transacoes.filter(conta=conta)
        if status:
            transacoes = transacoes.filter(status=status)
    
    # Paginação
    paginator = Paginator(transacoes, 20)
    page = request.GET.get('page')
    transacoes_paginadas = paginator.get_page(page)
    
    # Totais
    total_receitas = transacoes.filter(tipo='receita', status='paga').aggregate(
        total=Sum('valor'))['total'] or Decimal('0.00')
    total_despesas = transacoes.filter(tipo='despesa', status='paga').aggregate(
        total=Sum('valor'))['total'] or Decimal('0.00')
    
    context = {
        'transacoes': transacoes_paginadas,
        'filtro_form': filtro_form,
        'total_receitas': total_receitas,
        'total_despesas': total_despesas,
        'saldo': total_receitas - total_despesas,
    }
    
    return render(request, 'transactions/transacao_list.html', context)


@login_required
def transacao_create_view(request):
    """Criar nova transação"""
    casa = request.user.casa
    if not casa:
        messages.warning(request, 'Você precisa estar associado a uma casa.')
        return redirect('dashboard')
    
    # Obter tipo da URL (GET) ou do POST
    tipo = request.POST.get('tipo') or request.GET.get('tipo', 'despesa')
    
    if request.method == 'POST':
        # Verificar se é formulário rápido
        if request.POST.get('quick') == '1':
            # Criar transação diretamente dos dados do formulário rápido
            from datetime import date
            try:
                transacao = Transacao.objects.create(
                    casa=casa,
                    titulo=request.POST.get('titulo'),
                    valor=request.POST.get('valor'),
                    data=request.POST.get('data') or date.today(),
                    categoria_id=request.POST.get('categoria'),
                    conta_id=request.POST.get('conta'),
                    status=request.POST.get('status', 'paga'),
                    pago_por=request.user,
                    tipo=request.POST.get('tipo')
                )
                messages.success(request, f'✨ Transação "{transacao.titulo}" criada rapidamente!')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Erro ao criar transação: {str(e)}')
                return redirect('dashboard')
        else:
            # Formulário completo
            form = TransacaoForm(request.POST, request.FILES, usuario=request.user, casa=casa, tipo=tipo)
            if form.is_valid():
                transacao = form.save()
                # Para receitas, sempre definir status como "paga"
                if tipo == 'receita':
                    transacao.status = 'paga'
                    transacao.save()
                tipo_msg = 'Receita' if tipo == 'receita' else 'Despesa'
                messages.success(request, f'{tipo_msg} "{transacao.titulo}" criada com sucesso!')
                return redirect('transacao_list')
    else:
        form = TransacaoForm(usuario=request.user, casa=casa, tipo=tipo)
    
    # Buscar títulos anteriores com valores médios para autocomplete
    from django.db.models import Avg, Count
    titulos_anteriores = Transacao.objects.filter(
        casa=casa,
        tipo=tipo
    ).values('titulo', 'categoria_id').annotate(
        valor_medio=Avg('valor'),
        quantidade=Count('id')
    ).order_by('-quantidade', 'titulo')[:50]  # Top 50 mais usados
    
    title = f'Nova {"Despesa" if tipo == "despesa" else "Receita"}'
    return render(request, 'transactions/transacao_form_new.html', {
        'form': form,
        'title': title,
        'tipo': tipo,
        'titulos_anteriores': titulos_anteriores
    })


@login_required
def transacao_update_view(request, pk):
    """Atualizar transação"""
    casa = request.user.casa
    transacao = get_object_or_404(Transacao, pk=pk, casa=casa)
    
    if request.method == 'POST':
        form = TransacaoForm(
            request.POST,
            request.FILES,
            instance=transacao,
            usuario=request.user,
            casa=casa,
            tipo=transacao.tipo
        )
        if form.is_valid():
            transacao = form.save()
            messages.success(request, f'Transação "{transacao.titulo}" atualizada com sucesso!')
            return redirect('transacao_list')
    else:
        form = TransacaoForm(instance=transacao, usuario=request.user, casa=casa, tipo=transacao.tipo)
    
    return render(request, 'transactions/transacao_form.html', {
        'form': form,
        'title': 'Editar Transação',
        'transacao': transacao,
        'tipo': transacao.tipo
    })


@login_required
def transacao_delete_view(request, pk):
    """Deletar transação"""
    casa = request.user.casa
    
    if not casa:
        messages.error(request, 'Você não está associado a uma casa.')
        return redirect('transacao_list')
    
    transacao = get_object_or_404(Transacao, pk=pk, casa=casa)
    
    if request.method == 'POST':
        titulo = transacao.titulo
        transacao_id = transacao.id
        
        try:
            # Log da tentativa de exclusão
            logger.info(f"Usuário {request.user.username} tentando excluir transação ID {transacao_id}: {titulo}")
            
            transacao.delete()
            
            logger.info(f"Transação ID {transacao_id} excluída com sucesso")
            messages.success(request, f'Transação "{titulo}" excluída com sucesso!')
            
        except Exception as e:
            logger.error(f"Erro ao excluir transação ID {transacao_id}: {type(e).__name__}: {e}")
            messages.error(request, f'Erro ao excluir transação: {str(e)}')
        
        return redirect('transacao_list')
    
    return render(request, 'transactions/transacao_confirm_delete.html', {'transacao': transacao})


# ===========================
# Relatórios
# ===========================

@login_required
def relatorios_view(request):
    """View de relatórios"""
    casa = request.user.casa
    if not casa:
        messages.warning(request, 'Você precisa estar associado a uma casa.')
        return redirect('dashboard')
    
    # Obter período (padrão: últimos 12 meses)
    hoje = timezone.now().date()
    mes_inicio = (hoje - timedelta(days=365)).replace(day=1)
    
    # Despesas por categoria
    despesas_categoria = Transacao.objects.filter(
        casa=casa,
        tipo='despesa',
        data__gte=mes_inicio,
        status='paga'
    ).values('categoria__nome', 'categoria__cor').annotate(
        total=Sum('valor')
    ).order_by('-total')
    
    # Receitas por categoria
    receitas_categoria = Transacao.objects.filter(
        casa=casa,
        tipo='receita',
        data__gte=mes_inicio,
        status='paga'
    ).values('categoria__nome', 'categoria__cor').annotate(
        total=Sum('valor')
    ).order_by('-total')
    
    # Evolução mensal (últimos 12 meses)
    evolucao_mensal = []
    for i in range(12):
        mes = (hoje.replace(day=1) - timedelta(days=30*i))
        primeiro_dia = mes.replace(day=1)
        if mes.month == 12:
            ultimo_dia = mes.replace(day=31)
        else:
            ultimo_dia = (mes.replace(month=mes.month+1, day=1) - timedelta(days=1))
        
        receitas = Transacao.objects.filter(
            casa=casa,
            tipo='receita',
            data__gte=primeiro_dia,
            data__lte=ultimo_dia,
            status='paga'
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        despesas = Transacao.objects.filter(
            casa=casa,
            tipo='despesa',
            data__gte=primeiro_dia,
            data__lte=ultimo_dia,
            status='paga'
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        evolucao_mensal.append({
            'mes': mes.strftime('%b/%Y'),
            'receitas': float(receitas),
            'despesas': float(despesas),
            'saldo': float(receitas - despesas)
        })
    
    evolucao_mensal.reverse()
    
    # Despesas por conta
    despesas_conta = Transacao.objects.filter(
        casa=casa,
        tipo='despesa',
        data__gte=mes_inicio,
        status='paga'
    ).values('conta__nome').annotate(
        total=Sum('valor')
    ).order_by('-total')
    
    context = {
        'despesas_categoria': despesas_categoria,
        'receitas_categoria': receitas_categoria,
        'evolucao_mensal': evolucao_mensal,
        'despesas_conta': despesas_conta,
    }
    
    return render(request, 'relatorios.html', context)


@login_required
def exportar_csv_view(request):
    """Exportar transações para CSV"""
    casa = request.user.casa
    if not casa:
        return HttpResponse('Erro: você não está associado a uma casa.', status=400)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="transacoes_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Data', 'Tipo', 'Título', 'Categoria', 'Conta', 'Valor', 'Status', 'Pago Por'])
    
    transacoes = Transacao.objects.filter(casa=casa).order_by('-data')
    
    for t in transacoes:
        writer.writerow([
            t.data.strftime('%d/%m/%Y'),
            t.get_tipo_display(),
            t.titulo,
            t.categoria.nome,
            t.conta.nome,
            f'R$ {t.valor}',
            t.get_status_display(),
            t.pago_por.get_full_name() or t.pago_por.username
        ])
    
    return response


@login_required
def exportar_pdf_view(request):
    """Exportar relatório para PDF"""
    casa = request.user.casa
    if not casa:
        return HttpResponse('Erro: você não está associado a uma casa.', status=400)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_{timezone.now().date()}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0d6efd'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Título
    elements.append(Paragraph(f'Relatório Financeiro - {casa.nome}', title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Resumo
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    
    receitas_mes = Transacao.objects.filter(
        casa=casa,
        tipo='receita',
        data__gte=primeiro_dia_mes,
        status='paga'
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    despesas_mes = Transacao.objects.filter(
        casa=casa,
        tipo='despesa',
        data__gte=primeiro_dia_mes,
        status='paga'
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    resumo_data = [
        ['Descrição', 'Valor'],
        ['Receitas do Mês', f'R$ {receitas_mes:.2f}'],
        ['Despesas do Mês', f'R$ {despesas_mes:.2f}'],
        ['Saldo do Mês', f'R$ {(receitas_mes - despesas_mes):.2f}'],
    ]
    
    resumo_table = Table(resumo_data, colWidths=[4*inch, 2*inch])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(resumo_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Construir PDF
    doc.build(elements)
    
    return response


# ===========================
# Views de Autenticação Biométrica (WebAuthn)
# ===========================

def biometria_challenge_view(request):
    """Gera um challenge para autenticação biométrica"""
    # Aceitar requisições AJAX ou POST normais do formulário de login
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    is_post = request.method == 'POST'
    
    if not (is_ajax or is_post):
        logger.warning(f"Requisição inválida ao challenge de {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({'error': 'Requisição inválida'}, status=400)
    
    # Gerar challenge aleatório (32 bytes = 256 bits)
    challenge = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
    
    # Armazenar challenge e timestamp na sessão
    request.session['webauthn_challenge'] = challenge
    request.session['webauthn_challenge_timestamp'] = timezone.now().timestamp()
    
    # Buscar credenciais existentes (se o usuário estiver autenticado)
    allow_credentials = []
    if request.user.is_authenticated:
        from .models import CredencialBiometrica
        credenciais = CredencialBiometrica.objects.filter(usuario=request.user, ativa=True)
        allow_credentials = [{'id': cred.credential_id, 'type': 'public-key'} for cred in credenciais]
    else:
        # Buscar todas as credenciais ativas para permitir login
        from .models import CredencialBiometrica
        credenciais = CredencialBiometrica.objects.filter(ativa=True)
        allow_credentials = [{'id': cred.credential_id, 'type': 'public-key'} for cred in credenciais]
    
    logger.debug(f"Challenge gerado para {len(allow_credentials)} credenciais")
    
    return JsonResponse({
        'challenge': challenge,
        'allowCredentials': allow_credentials,
        'timeout': 60000,
        'userVerification': 'preferred',
        'rpId': request.get_host().split(':')[0]
    })


@require_http_methods(["POST"])
def biometria_verify_view(request):
    """Verifica a autenticação biométrica com validação melhorada"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logger.warning(f"Tentativa de acesso inválido à biometria de {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({'error': 'Requisição inválida'}, status=400)
    
    try:
        data = json.loads(request.body)
        credential_id = data.get('id')
        client_data = data.get('response', {})
        
        if not credential_id:
            return JsonResponse({'success': False, 'error': 'Credencial não fornecida'})
        
        # Buscar credencial
        from .models import CredencialBiometrica
        try:
            credencial = CredencialBiometrica.objects.get(
                credential_id=credential_id,
                ativa=True
            )
        except CredencialBiometrica.DoesNotExist:
            logger.warning(f"Credencial não encontrada: {credential_id}")
            return JsonResponse({
                'success': False,
                'error': 'Credencial não encontrada'
            })
        
        # VALIDAÇÃO 1: Verificar challenge
        stored_challenge = request.session.get('webauthn_challenge')
        if not stored_challenge:
            logger.warning(f"Challenge expirado para credencial {credential_id}")
            return JsonResponse({
                'success': False,
                'error': 'Challenge expirado ou inválido'
            })
        
        # VALIDAÇÃO 2: Verificar timestamp do challenge (máximo 60 segundos)
        challenge_timestamp = request.session.get('webauthn_challenge_timestamp', 0)
        current_timestamp = timezone.now().timestamp()
        if current_timestamp - challenge_timestamp > 60:
            logger.warning(f"Challenge expirado por timeout: {credential_id}")
            del request.session['webauthn_challenge']
            return JsonResponse({
                'success': False,
                'error': 'Challenge expirado. Por favor, tente novamente.'
            })
        
        # VALIDAÇÃO 3: Verificar sign_count (protege contra clonagem)
        authenticator_data = client_data.get('authenticatorData', {})
        new_sign_count = authenticator_data.get('signCount', 0)
        
        if new_sign_count > 0 and new_sign_count <= credencial.sign_count:
            logger.error(f"⚠️ ALERTA DE SEGURANÇA: Sign count inválido para {credencial.usuario.username}")
            logger.error(f"   Esperado: > {credencial.sign_count}, Recebido: {new_sign_count}")
            return JsonResponse({
                'success': False,
                'error': 'Erro de segurança. Credencial pode estar comprometida.'
            })
        
        # VALIDAÇÃO 4: Verificar se o usuário não está bloqueado
        if hasattr(credencial.usuario, 'is_active') and not credencial.usuario.is_active:
            logger.warning(f"Tentativa de login com usuário inativo: {credencial.usuario.username}")
            return JsonResponse({
                'success': False,
                'error': 'Usuário inativo'
            })
        
        # Atualizar credencial
        credencial.ultimo_uso = timezone.now()
        credencial.sign_count = max(new_sign_count, credencial.sign_count + 1)
        credencial.save()
        
        # Fazer login do usuário
        login(request, credencial.usuario)
        
        # Limpar challenge da sessão
        if 'webauthn_challenge' in request.session:
            del request.session['webauthn_challenge']
        if 'webauthn_challenge_timestamp' in request.session:
            del request.session['webauthn_challenge_timestamp']
        
        logger.info(f"✅ Login biométrico bem-sucedido: {credencial.usuario.username}")
        messages.success(request, f'✓ Login realizado com sucesso via biometria!')
        
        return JsonResponse({
            'success': True,
            'redirect': '/'
        })
        
    except json.JSONDecodeError:
        logger.error("Erro ao decodificar JSON na verificação biométrica")
        return JsonResponse({
            'success': False,
            'error': 'Dados inválidos'
        })
    except Exception as e:
        logger.exception(f"Erro na verificação biométrica: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erro interno ao processar autenticação'
        })


@login_required
def biometria_register_view(request):
    """Registra uma nova credencial biométrica"""
    if request.method == 'GET':
        # Gerar challenge para registro
        challenge = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        request.session['webauthn_register_challenge'] = challenge
        
        user_id = base64.urlsafe_b64encode(str(request.user.id).encode()).decode('utf-8').rstrip('=')
        
        return JsonResponse({
            'challenge': challenge,
            'user': {
                'id': user_id,
                'name': request.user.username,
                'displayName': request.user.get_full_name() or request.user.username
            },
            'rp': {
                'name': 'Controle de Despesas',
                'id': request.get_host().split(':')[0]
            },
            'pubKeyCredParams': [
                {'type': 'public-key', 'alg': -7},  # ES256
                {'type': 'public-key', 'alg': -257}  # RS256
            ],
            'timeout': 60000,
            'authenticatorSelection': {
                'authenticatorAttachment': 'platform',
                'requireResidentKey': False,
                'userVerification': 'preferred'
            }
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Verificar challenge
            stored_challenge = request.session.get('webauthn_register_challenge')
            if not stored_challenge:
                return JsonResponse({
                    'success': False,
                    'error': 'Challenge expirado'
                })
            
            # Salvar credencial
            from .models import CredencialBiometrica
            credencial = CredencialBiometrica.objects.create(
                usuario=request.user,
                credential_id=data.get('id'),
                public_key=data.get('response', {}).get('publicKey', ''),
                nome_dispositivo=data.get('deviceName', 'Dispositivo')
            )
            
            # Ativar biometria no usuário
            request.user.biometria_habilitada = True
            request.user.save()
            
            # Limpar challenge
            del request.session['webauthn_register_challenge']
            
            messages.success(request, '✓ Biometria configurada com sucesso!')
            
            return JsonResponse({
                'success': True,
                'message': 'Credencial registrada com sucesso'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


@login_required
def biometria_settings_view(request):
    """Página de configurações de biometria"""
    from .models import CredencialBiometrica
    credenciais = CredencialBiometrica.objects.filter(usuario=request.user)
    
    context = {
        'credenciais': credenciais,
        'biometria_habilitada': request.user.biometria_habilitada
    }
    
    return render(request, 'auth/biometria_settings.html', context)


@login_required
@require_http_methods(["POST"])
def biometria_delete_view(request, credencial_id):
    """Remove uma credencial biométrica"""
    from .models import CredencialBiometrica
    
    try:
        credencial = get_object_or_404(
            CredencialBiometrica,
            id=credencial_id,
            usuario=request.user
        )
        
        credencial.delete()
        
        # Desativar biometria se não houver mais credenciais
        if not CredencialBiometrica.objects.filter(usuario=request.user).exists():
            request.user.biometria_habilitada = False
            request.user.save()
        
        messages.success(request, 'Credencial removida com sucesso!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect('biometria_settings')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Erro ao remover credencial: {str(e)}')
        return redirect('biometria_settings')


# ===========================
# Views de Chat Financeiro
# ===========================

def save_chat_transaction(user, transaction_data, original_message, status='paga'):
    """Salva uma transação criada via chat no banco de dados."""
    from datetime import datetime
    from decimal import Decimal
    
    # Obter a casa do usuário
    if not user.casa:
        raise ValueError("Usuário não possui uma casa associada")
    
    # Obter ou criar conta padrão
    account_name = transaction_data.get('account', 'Carteira')
    conta, _ = Conta.objects.get_or_create(
        casa=user.casa,
        nome=account_name,
        defaults={'tipo': 'corrente', 'saldo_inicial': Decimal('0.00'), 'ativa': True}
    )
    
    # Obter ou criar categoria
    category_name = transaction_data.get('category', 'Outros')
    tipo_transacao = transaction_data.get('type', 'despesa')
    tipo_categoria = 'despesa' if tipo_transacao == 'despesa' else 'receita'
    
    categoria, _ = Categoria.objects.get_or_create(
        casa=user.casa,
        nome=category_name,
        defaults={'tipo': tipo_categoria, 'cor': '#6c757d', 'icone': '💰', 'ativa': True}
    )
    
    # Processar data - usar a data fornecida pela IA ou a data atual se não informada
    from zoneinfo import ZoneInfo
    from datetime import datetime as dt_datetime
    tz_br = ZoneInfo('America/Sao_Paulo')
    
    # Tentar obter a data do transaction_data (formato ISO: YYYY-MM-DD)
    date_str = transaction_data.get('date')
    if date_str:
        try:
            # Parse da data ISO fornecida pela IA
            data_transacao = dt_datetime.fromisoformat(date_str).date()
            logger.info(f"Data obtida da IA: {data_transacao}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao converter data '{date_str}': {e}. Usando data atual.")
            data_transacao = timezone.now().astimezone(tz_br).date()
    else:
        # Se não houver data, usar data atual
        data_transacao = timezone.now().astimezone(tz_br).date()
        logger.info(f"Nenhuma data fornecida, usando data atual (timezone BR): {data_transacao}")
    
    # Se estamos criando uma transação definitiva, tentar unir com
    # uma transação pendente similar (mesmo valor/data) para evitar duplicação.
    if status == 'paga':
        try:
            from datetime import timedelta
            from django.utils import timezone as dj_timezone

            cutoff = dj_timezone.now() - timedelta(days=2)
            amount_val = Decimal(str(transaction_data.get('amount', 0)))

            similar = Transacao.objects.filter(
                casa=user.casa,
                valor=amount_val,
                data=data_transacao,
                status='pendente',
                criada_em__gte=cutoff
            ).order_by('-criada_em')

            if similar.exists():
                transacao = similar.first()
                transacao.conta = conta
                transacao.categoria = categoria
                transacao.tipo = tipo_transacao
                transacao.titulo = transaction_data.get('title', original_message[:100])
                transacao.observacao = transaction_data.get('notes', f'Atualizado via chat: {original_message}')
                transacao.pago_por = user
                transacao.status = 'paga'
                transacao.save()
                logger.info(f"Transação pendente atualizada para paga: ID {transacao.id}")
                return transacao
        except Exception as e:
            logger.warning(f"Erro ao tentar unir com transação pendente: {e}")

    # Criar a transação normalmente
    transacao = Transacao.objects.create(
        casa=user.casa,
        conta=conta,
        categoria=categoria,
        tipo=tipo_transacao,
        valor=Decimal(str(transaction_data.get('amount', 0))),
        titulo=transaction_data.get('title', original_message[:100]),
        data=data_transacao,
        observacao=transaction_data.get('notes', f'Criado via chat: {original_message}'),
        pago_por=user,
        status=status
    )

    return transacao


def update_chat_transaction(transaction_id, user, transaction_data, original_message):
    """Atualiza uma transação existente criada via chat."""
    from datetime import datetime as dt_datetime
    from decimal import Decimal
    from zoneinfo import ZoneInfo
    
    try:
        # Buscar a transação
        transacao = Transacao.objects.get(id=transaction_id, casa=user.casa)
    except Transacao.DoesNotExist:
        raise ValueError(f"Transação {transaction_id} não encontrada")
    
    # Atualizar campos se fornecidos
    if 'amount' in transaction_data and transaction_data['amount']:
        transacao.valor = Decimal(str(transaction_data['amount']))
    
    if 'title' in transaction_data and transaction_data['title']:
        transacao.titulo = transaction_data['title']
    
    if 'type' in transaction_data and transaction_data['type']:
        transacao.tipo = transaction_data['type']
    
    # Atualizar categoria se fornecida
    if 'category' in transaction_data and transaction_data['category']:
        category_name = transaction_data['category']
        tipo_categoria = transacao.tipo  # Usar o tipo atual da transação
        categoria, _ = Categoria.objects.get_or_create(
            casa=user.casa,
            nome=category_name,
            defaults={'tipo': tipo_categoria, 'cor': '#6c757d', 'icone': '💰', 'ativa': True}
        )
        transacao.categoria = categoria
    
    # Atualizar conta se fornecida
    if 'account' in transaction_data and transaction_data['account']:
        account_name = transaction_data['account']
        conta, _ = Conta.objects.get_or_create(
            casa=user.casa,
            nome=account_name,
            defaults={'tipo': 'corrente', 'saldo_inicial': Decimal('0.00'), 'ativa': True}
        )
        transacao.conta = conta
    
    # Atualizar data se fornecida
    if 'date' in transaction_data and transaction_data['date']:
        date_str = transaction_data['date']
        try:
            data_transacao = dt_datetime.fromisoformat(date_str).date()
            transacao.data = data_transacao
            logger.info(f"Data atualizada: {data_transacao}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao converter data '{date_str}': {e}")
    
    # Atualizar observação
    if 'notes' in transaction_data and transaction_data['notes']:
        transacao.observacao = transaction_data['notes']
    else:
        # Adicionar nota de edição
        transacao.observacao = f"{transacao.observacao}\nEditado via chat: {original_message}"

    # Se era pendente, ao atualizar via chat assumimos que agora está definitiva
    if transacao.status == 'pendente':
        transacao.status = 'paga'

    transacao.save()
    logger.info(f"Transação {transaction_id} atualizada com sucesso")
    
    return transacao


def search_transactions(user, criteria):
    """
    Busca transações baseado em critérios fornecidos.
    Retorna QuerySet de transações que correspondem aos critérios.
    """
    from datetime import datetime as dt_datetime
    
    if not user.casa:
        return Transacao.objects.none()
    
    # Começar com todas as transações do usuário
    queryset = Transacao.objects.filter(casa=user.casa)
    
    # Filtrar por categoria
    if criteria.get('category'):
        queryset = queryset.filter(categoria__nome__icontains=criteria['category'])
    
    # Filtrar por conta
    if criteria.get('account'):
        queryset = queryset.filter(conta__nome__icontains=criteria['account'])
    
    # Filtrar por data
    if criteria.get('date'):
        try:
            date_obj = dt_datetime.fromisoformat(criteria['date']).date()
            queryset = queryset.filter(data=date_obj)
        except (ValueError, TypeError):
            pass
    
    # Filtrar por valor (range)
    if criteria.get('min_amount'):
        queryset = queryset.filter(valor__gte=criteria['min_amount'])
    if criteria.get('max_amount'):
        queryset = queryset.filter(valor__lte=criteria['max_amount'])
    
    # Filtrar por título/descrição
    if criteria.get('title_contains'):
        queryset = queryset.filter(titulo__icontains=criteria['title_contains'])
    
    # Ordenar por data (mais recentes primeiro)
    queryset = queryset.order_by('-data', '-id')
    
    # Limitar a 10 resultados
    return queryset[:10]


def format_transaction_preview(transacao):
    """Formata uma transação para exibição no chat."""
    icone = '💸' if transacao.tipo == 'despesa' else '💰'
    return (
        f"{icone} {transacao.tipo.upper()}\n"
        f"Valor: R$ {transacao.valor:.2f}\n"
        f"Categoria: {transacao.categoria.nome}\n"
        f"Conta: {transacao.conta.nome}\n"
        f"Data: {transacao.data.strftime('%d/%m/%Y')}"
    )

