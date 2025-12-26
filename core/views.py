
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import logging
from reportlab.lib.pagesizes import letter, A4
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
    """Deletar conta"""
    casa = request.user.casa
    conta = get_object_or_404(Conta, pk=pk, casa=casa)
    
    if request.method == 'POST':
        nome = conta.nome
        conta.delete()
        messages.success(request, f'Conta "{nome}" excluída com sucesso!')
        return redirect('conta_list')
    
    return render(request, 'accounts/conta_confirm_delete.html', {'conta': conta})


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
    """Deletar categoria"""
    casa = request.user.casa
    categoria = get_object_or_404(Categoria, pk=pk, casa=casa)
    
    if request.method == 'POST':
        nome = categoria.nome
        categoria.delete()
        messages.success(request, f'Categoria "{nome}" excluída com sucesso!')
        return redirect('categoria_list')
    
    return render(request, 'categories/categoria_confirm_delete.html', {'categoria': categoria})


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
    transacao = get_object_or_404(Transacao, pk=pk, casa=casa)
    
    if request.method == 'POST':
        titulo = transacao.titulo
        transacao.delete()
        messages.success(request, f'Transação "{titulo}" excluída com sucesso!')
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

import os
import base64
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

def biometria_challenge_view(request):
    """Gera um challenge para autenticação biométrica"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Requisição inválida'}, status=400)
    
    # Gerar challenge aleatório
    challenge = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
    
    # Armazenar challenge na sessão
    request.session['webauthn_challenge'] = challenge
    
    # Buscar credenciais existentes (se o usuário estiver autenticado)
    allow_credentials = []
    if request.user.is_authenticated:
        from .models import CredencialBiometrica
        credenciais = CredencialBiometrica.objects.filter(usuario=request.user, ativa=True)
        allow_credentials = [{'id': cred.credential_id} for cred in credenciais]
    else:
        # Buscar todas as credenciais ativas para permitir login
        from .models import CredencialBiometrica
        credenciais = CredencialBiometrica.objects.filter(ativa=True)
        allow_credentials = [{'id': cred.credential_id} for cred in credenciais]
    
    return JsonResponse({
        'challenge': challenge,
        'allowCredentials': allow_credentials,
        'timeout': 60000,
        'userVerification': 'preferred'
    })


@require_http_methods(["POST"])
def biometria_verify_view(request):
    """Verifica a autenticação biométrica"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Requisição inválida'}, status=400)
    
    try:
        data = json.loads(request.body)
        credential_id = data.get('id')
        
        # Buscar credencial
        from .models import CredencialBiometrica
        try:
            credencial = CredencialBiometrica.objects.get(
                credential_id=credential_id,
                ativa=True
            )
        except CredencialBiometrica.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Credencial não encontrada'
            })
        
        # Verificar challenge (simplificado para MVP)
        stored_challenge = request.session.get('webauthn_challenge')
        if not stored_challenge:
            return JsonResponse({
                'success': False,
                'error': 'Challenge expirado ou inválido'
            })
        
        # Atualizar último uso
        credencial.ultimo_uso = timezone.now()
        credencial.sign_count += 1
        credencial.save()
        
        # Fazer login do usuário
        login(request, credencial.usuario)
        
        # Limpar challenge da sessão
        del request.session['webauthn_challenge']
        
        messages.success(request, f'✓ Login realizado com sucesso via biometria!')
        
        return JsonResponse({
            'success': True,
            'redirect': '/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
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


def save_chat_history(user, user_message, assistant_response, intent, transcribed_text=None):
    """Salva o histórico de conversação do chat."""
    from core.models import ChatHistory
    
    ChatHistory.objects.create(
        usuario=user,
        user_message=user_message,
        assistant_response=assistant_response,
        intent=intent,
        transcribed_text=transcribed_text
    )


@login_required
def chat_interface_view(request):
    """Renderiza a interface de chat financeiro."""
    return render(request, 'chat/interface.html')


@api_view(['GET'])
def chat_history_view(request):
    """Retorna o histórico recente de conversas do chat."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Usuário não autenticado"},
            status=rest_status.HTTP_401_UNAUTHORIZED
        )
    
    from core.models import ChatHistory
    
    # Buscar últimas 20 mensagens
    history = ChatHistory.objects.filter(
        usuario=request.user
    ).order_by('-created_at')[:20]
    
    # Reverter ordem para exibir do mais antigo ao mais recente
    history = list(reversed(history))
    
    messages = []
    for entry in history:
        messages.append({
            'role': 'user',
            'content': entry.user_message,
            'timestamp': entry.created_at.isoformat()
        })
        messages.append({
            'role': 'assistant',
            'content': entry.assistant_response,
            'intent': entry.intent,
            'timestamp': entry.created_at.isoformat()
        })
    
    return Response({
        'messages': messages,
        'count': len(messages)
    }, status=rest_status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def chat_message_view(request):
    """
    Endpoint principal para processar mensagens do chat financeiro.
    Aceita texto ou áudio, envia para a OpenAI e retorna resposta estruturada.
    """
    logger_chat.info(f"Recebida requisição de chat. Content-Type: {request.content_type}")
    logger_chat.info(f"Data recebida: {request.data}")
    
    serializer = ChatMessageSerializer(data=request.data)
    if not serializer.is_valid():
        logger_chat.error(f"Erro de validação: {serializer.errors}")
        return Response(
            {"error": serializer.errors},
            status=rest_status.HTTP_400_BAD_REQUEST
        )

    validated_data = serializer.validated_data
    message_text = validated_data.get('message', '').strip()
    audio_file = validated_data.get('audio')
    context = validated_data.get('context', [])

    try:
        client = OpenAIClient()

        # Se recebeu áudio, transcreve primeiro
        transcribed_text = None
        if audio_file:
            logger_chat.info("Transcrevendo áudio do usuário...")
            transcribed_text = client.transcribe_audio(audio_file)
            message_text = transcribed_text
            logger_chat.info(f"Áudio transcrito: {transcribed_text[:100]}...")

        if not message_text:
            return Response(
                {"error": "Não foi possível obter texto da mensagem ou transcrição."},
                status=rest_status.HTTP_400_BAD_REQUEST
            )

        # Se o usuário mencionar edição, adicionar transações recentes ao contexto
        if any(word in message_text.lower() for word in ['edit', 'editar', 'alterar', 'mudar', 'corrigir', 'atualizar']):
            if request.user.is_authenticated and request.user.casa:
                recent_transactions = Transacao.objects.filter(
                    casa=request.user.casa
                ).order_by('-data', '-id')[:5]
                
                if recent_transactions:
                    trans_list = "\n".join([
                        f"ID{t.id}: {t.data.strftime('%d/%m')} - {t.categoria.nome} - {t.conta.nome} - R$ {t.valor:.2f}"
                        for t in recent_transactions
                    ])
                    context.append({
                        'role': 'system',
                        'content': f"Transações recentes do usuário:\n{trans_list}"
                    })

        # Processa a mensagem com o modelo
        logger_chat.info(f"Processando mensagem: {message_text[:100]}...")
        parsed_response = client.parse_user_message(
            message=message_text,
            context=context
        )
        
        # Log detalhado da resposta da IA
        logger_chat.info(f"Resposta da IA - Intent: {parsed_response.get('intent')}")
        logger_chat.info(f"Resposta da IA - Clarification: {parsed_response.get('clarification_needed')}")
        logger_chat.info(f"Resposta da IA - Transaction: {parsed_response.get('transaction')}")

        # Adiciona o texto transcrito na resposta se houver
        if transcribed_text:
            parsed_response['transcribed_text'] = transcribed_text

        # Se a intenção for criar transação
        intent = parsed_response.get('intent')
        needs_clarification = parsed_response.get('clarification_needed', False)

        if intent == 'create_transaction':
            transaction_data = parsed_response.get('transaction')
            
            # A IA pode retornar uma transação (objeto) ou múltiplas (array)
            if isinstance(transaction_data, list):
                # Múltiplas transações
                logger_chat.info(f"IA retornou {len(transaction_data)} transações")
                saved_transactions = []
                
                for idx, trans_data in enumerate(transaction_data):
                    has_required_data = trans_data.get('amount') and trans_data.get('amount') > 0
                    
                    if has_required_data and request.user.is_authenticated:
                        try:
                            saved_transaction = save_chat_transaction(
                                user=request.user,
                                transaction_data=trans_data,
                                original_message=f"{message_text} (transação {idx+1}/{len(transaction_data)})"
                            )
                            saved_transactions.append(saved_transaction)
                            logger_chat.info(f"Transação {idx+1} salva: ID {saved_transaction.id}")
                        except Exception as e:
                            logger_chat.error(f"Erro ao salvar transação {idx+1}: {e}")
                
                if saved_transactions:
                    parsed_response['transaction_saved'] = True
                    parsed_response['transaction_ids'] = [t.id for t in saved_transactions]
                    
                    # Criar lista formatada das transações
                    trans_list = "\n".join([
                        f"  {i+1}. {t.titulo} - R$ {t.valor:.2f} ({t.categoria.nome})"
                        for i, t in enumerate(saved_transactions)
                    ])
                    
                    total = sum(t.valor for t in saved_transactions)
                    tipo = "despesas" if saved_transactions[0].tipo == "despesa" else "receitas"
                    icone = "💸" if saved_transactions[0].tipo == "despesa" else "💰"
                    
                    parsed_response['assistant_message'] = (
                        f"✅ {len(saved_transactions)} {tipo} registradas com sucesso!\n\n"
                        f"{trans_list}\n\n"
                        f"{icone} Total: R$ {total:.2f}"
                    )
                else:
                    parsed_response['transaction_saved'] = False
                    
            elif isinstance(transaction_data, dict):
                # Transação única
                has_required_data = (
                    transaction_data.get('amount') and
                    transaction_data.get('amount') > 0
                )
                
                if has_required_data and request.user.is_authenticated:
                    try:
                        # Usar o valor validado para pending_transaction_id (se enviado pelo frontend)
                        pending_transaction_id = validated_data.get('pending_transaction_id')

                        if pending_transaction_id:
                            # Editar transação existente
                            saved_transaction = update_chat_transaction(
                                transaction_id=pending_transaction_id,
                                user=request.user,
                                transaction_data=transaction_data,
                                original_message=message_text
                            )
                            logger_chat.info(f"Transação {saved_transaction.id} atualizada com sucesso")
                            parsed_response['transaction_id'] = saved_transaction.id
                            parsed_response['transaction_saved'] = True

                        else:
                            # Se a IA pediu esclarecimento, criar registro pendente ao invés de definitivo
                            if needs_clarification:
                                saved_transaction = save_chat_transaction(
                                    user=request.user,
                                    transaction_data=transaction_data,
                                    original_message=message_text,
                                    status='pendente'
                                )
                                logger_chat.info(f"Transação pendente criada: ID {saved_transaction.id}")
                                parsed_response['transaction_id'] = saved_transaction.id
                                parsed_response['transaction_pending'] = True
                                parsed_response['transaction_saved'] = False
                            else:
                                # Tentar encontrar uma transação 'pendente' recente do mesmo usuário
                                # e atualizá-la quando o frontend não enviou `pending_transaction_id`.
                                fallback_updated = None
                                try:
                                    from datetime import timedelta
                                    from django.utils import timezone as dj_timezone

                                    cutoff = dj_timezone.now() - timedelta(days=2)
                                    pend_qs = Transacao.objects.filter(
                                        casa=request.user.casa,
                                        pago_por=request.user,
                                        status='pendente',
                                        criada_em__gte=cutoff
                                    ).order_by('-criada_em')

                                    if pend_qs.exists():
                                        candidate = pend_qs.first()
                                        # Atualizar o candidato com os dados recebidos
                                        saved_candidate = update_chat_transaction(
                                            transaction_id=candidate.id,
                                            user=request.user,
                                            transaction_data=transaction_data,
                                            original_message=message_text
                                        )
                                        fallback_updated = saved_candidate
                                        logger_chat.info(f"Transação pendente encontrada e atualizada: ID {saved_candidate.id}")
                                except Exception as e:
                                    logger_chat.warning(f"Erro ao tentar fallback update de pendente: {e}")

                                if fallback_updated:
                                    parsed_response['transaction_id'] = fallback_updated.id
                                    parsed_response['transaction_saved'] = True
                                else:
                                    # Criar nova transação definitiva
                                    saved_transaction = save_chat_transaction(
                                        user=request.user,
                                        transaction_data=transaction_data,
                                        original_message=message_text,
                                        status='paga'
                                    )
                                    logger_chat.info(f"Transação salva com sucesso: ID {saved_transaction.id}")
                                    parsed_response['transaction_id'] = saved_transaction.id
                                    parsed_response['transaction_saved'] = True
                    except Exception as e:
                        logger_chat.error(f"Erro ao salvar/atualizar transação: {e}")
                        parsed_response['transaction_saved'] = False
                        parsed_response['save_error'] = str(e)
                else:
                    # Não há dados suficientes para criar a transação
                    logger_chat.warning(f"Dados insuficientes para criar transação: {transaction_data}")
                    parsed_response['transaction_saved'] = False
                    if not needs_clarification:
                        # Forçar clarification se não foi detectado pela IA
                        parsed_response['clarification_needed'] = True
                        
                        # Verificar o que está faltando
                        missing = []
                        if not transaction_data.get('amount'):
                            missing.append("o valor")
                        if not transaction_data.get('title') and not transaction_data.get('category'):
                            missing.append("a descrição ou categoria")
                        
                        if missing:
                            missing_text = " e ".join(missing)
                            parsed_response['assistant_message'] = (
                                f"⚠️ Para registrar a transação, preciso saber {missing_text}.\n\n"
                                f"💡 Exemplo: 'Gastei 50 reais no mercado'"
                            )
                        elif 'assistant_message' in parsed_response and 'valor' not in parsed_response['assistant_message'].lower():
                            parsed_response['assistant_message'] += "\n\n💡 Por favor, me diga o valor da transação."
        
        # Se a intenção for editar transação existente
        elif intent == 'edit_transaction':
            search_criteria = parsed_response.get('search_criteria', {})
            transaction_data = parsed_response.get('transaction', {})
            
            logger_chat.info(f"🔍 EDIÇÃO - Critérios de busca: {search_criteria}")
            logger_chat.info(f"🔍 EDIÇÃO - Dados da transação: {transaction_data}")
            
            if request.user.is_authenticated and not needs_clarification:
                try:
                    # Buscar transações que correspondam aos critérios
                    found_transactions = search_transactions(
                        user=request.user,
                        criteria=search_criteria
                    )
                    
                    logger_chat.info(f"🔍 EDIÇÃO - Transações encontradas: {len(found_transactions)}")
                    if len(found_transactions) > 0:
                        logger_chat.info(f"🔍 EDIÇÃO - Primeira transação: {found_transactions[0].titulo} - R$ {found_transactions[0].valor} - {found_transactions[0].data}")
                    
                    if len(found_transactions) == 0:
                        parsed_response['assistant_message'] = (
                            "🔍 Não encontrei nenhuma transação com essas características.\n\n"
                            "💡 Dica: Tente mencionar:\n"
                            "• A data exata (ex: 'dia 08/11')\n"
                            "• O valor aproximado (ex: 'de R$ 250')\n"
                            "• A categoria ou descrição (ex: 'mercado', 'gasolina')\n"
                            "• A conta usada (ex: 'cartão de crédito', 'conta corrente')"
                        )
                        parsed_response['clarification_needed'] = True
                    elif len(found_transactions) == 1:
                        # Atualizar a transação encontrada
                        old_transaction = found_transactions[0]
                        saved_transaction = update_chat_transaction(
                            transaction_id=old_transaction.id,
                            user=request.user,
                            transaction_data=transaction_data,
                            original_message=message_text
                        )
                        parsed_response['transaction_id'] = saved_transaction.id
                        parsed_response['transaction_saved'] = True
                        
                        # Mostrar o que foi alterado
                        changes = []
                        if transaction_data.get('amount') and old_transaction.valor != transaction_data['amount']:
                            changes.append(f"Valor: R$ {old_transaction.valor:.2f} → R$ {saved_transaction.valor:.2f}")
                        if transaction_data.get('title') and old_transaction.titulo != transaction_data['title']:
                            changes.append(f"Descrição: {old_transaction.titulo} → {saved_transaction.titulo}")
                        if transaction_data.get('date') and str(old_transaction.data) != transaction_data['date']:
                            changes.append(f"Data: {old_transaction.data.strftime('%d/%m/%Y')} → {saved_transaction.data.strftime('%d/%m/%Y')}")
                        
                        changes_text = "\n".join([f"  • {c}" for c in changes]) if changes else "  • Dados atualizados"
                        
                        parsed_response['assistant_message'] = (
                            f"✅ Transação atualizada com sucesso!\n\n"
                            f"📝 Alterações:\n{changes_text}\n\n"
                            f"{format_transaction_preview(saved_transaction)}"
                        )
                    else:
                        # Múltiplas transações encontradas
                        trans_list = "\n".join([
                            f"  {i+1}. {t.data.strftime('%d/%m/%Y')} - {t.titulo} - R$ {t.valor:.2f} ({t.conta.nome})"
                            for i, t in enumerate(found_transactions[:5])
                        ])
                        
                        mais = f"\n  ... e mais {len(found_transactions) - 5} transações" if len(found_transactions) > 5 else ""
                        
                        parsed_response['assistant_message'] = (
                            f"🔍 Encontrei {len(found_transactions)} transações:\n\n"
                            f"{trans_list}{mais}\n\n"
                            f"💡 Para editar, seja mais específico mencionando:\n"
                            f"• A data exata (ex: 'a transação do dia 08/11')\n"
                            f"• O valor exato (ex: 'a de R$ {found_transactions[0].valor:.2f}')"
                        )
                        parsed_response['clarification_needed'] = True
                        
                except Exception as e:
                    logger_chat.error(f"Erro ao buscar/editar transação: {e}")
                    parsed_response['assistant_message'] = f"Erro ao processar edição: {str(e)}"
                    parsed_response['clarification_needed'] = True
        
        # Se a intenção for gerar relatório
        elif intent == 'query_summary':
            query = parsed_response.get('query', {})
            logger_chat.info(f"📊 RELATÓRIO - Query recebida: {query}")
            
            if request.user.is_authenticated and not needs_clarification:
                try:
                    from datetime import datetime as dt_datetime, timedelta
                    from django.db.models import Sum, Count, Q
                    
                    # Extrair parâmetros do relatório
                    # A IA retorna: {"summary_type": "month_total", "period": {"start_date": "...", "end_date": "..."}}
                    period_obj = query.get('period', {})
                    start_date = period_obj.get('start_date')
                    end_date = period_obj.get('end_date')
                    category = query.get('category')
                    transaction_type = query.get('type')  # despesa, receita
                    
                    # Definir período
                    hoje = dt_datetime.now().date()
                    
                    # Se a IA forneceu datas, usar elas
                    if start_date and end_date:
                        try:
                            inicio = dt_datetime.fromisoformat(start_date).date()
                            fim = dt_datetime.fromisoformat(end_date).date()
                        except:
                            # Fallback para mês atual
                            inicio = hoje.replace(day=1)
                            if hoje.month == 12:
                                fim = hoje.replace(day=31)
                            else:
                                proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
                                fim = proximo_mes - timedelta(days=1)
                    else:
                        # Fallback para mês atual
                        inicio = hoje.replace(day=1)
                        if hoje.month == 12:
                            fim = hoje.replace(day=31)
                        else:
                            proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
                            fim = proximo_mes - timedelta(days=1)
                    
                    logger_chat.info(f"📊 RELATÓRIO - Período: {inicio} a {fim}")
                    
                    # Buscar transações
                    queryset = Transacao.objects.filter(
                        casa=request.user.casa,
                        data__gte=inicio,
                        data__lte=fim
                    )
                    
                    if category:
                        queryset = queryset.filter(categoria__nome__icontains=category)
                    
                    if transaction_type:
                        queryset = queryset.filter(tipo=transaction_type)
                    
                    # Calcular totais
                    despesas = queryset.filter(tipo='despesa').aggregate(
                        total=Sum('valor'),
                        count=Count('id')
                    )
                    receitas = queryset.filter(tipo='receita').aggregate(
                        total=Sum('valor'),
                        count=Count('id')
                    )
                    
                    total_despesas = despesas['total'] or 0
                    total_receitas = receitas['total'] or 0
                    saldo = total_receitas - total_despesas
                    
                    # Totais por categoria
                    despesas_por_cat = queryset.filter(tipo='despesa').values(
                        'categoria__nome'
                    ).annotate(
                        total=Sum('valor'),
                        count=Count('id')
                    ).order_by('-total')[:5]
                    
                    receitas_por_cat = queryset.filter(tipo='receita').values(
                        'categoria__nome'
                    ).annotate(
                        total=Sum('valor'),
                        count=Count('id')
                    ).order_by('-total')[:5]
                    
                    # Formatar relatório
                    periodo_texto = f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
                    
                    relatorio = [
                        f"📊 **RELATÓRIO FINANCEIRO**",
                        f"📅 Período: {periodo_texto}",
                        "",
                        "💰 **RESUMO GERAL**",
                        f"• Receitas: R$ {total_receitas:,.2f} ({receitas['count']} transações)",
                        f"• Despesas: R$ {total_despesas:,.2f} ({despesas['count']} transações)",
                        f"• Saldo: R$ {saldo:,.2f}",
                        ""
                    ]
                    
                    if despesas_por_cat:
                        relatorio.append("📉 **TOP 5 DESPESAS POR CATEGORIA**")
                        for item in despesas_por_cat:
                            cat_nome = item['categoria__nome'] or 'Sem categoria'
                            relatorio.append(f"• {cat_nome}: R$ {item['total']:,.2f} ({item['count']} transações)")
                        relatorio.append("")
                    
                    if receitas_por_cat:
                        relatorio.append("📈 **TOP 5 RECEITAS POR CATEGORIA**")
                        for item in receitas_por_cat:
                            cat_nome = item['categoria__nome'] or 'Sem categoria'
                            relatorio.append(f"• {cat_nome}: R$ {item['total']:,.2f} ({item['count']} transações)")
                        relatorio.append("")
                    
                    # Adicionar análise
                    if saldo > 0:
                        relatorio.append(f"✅ Saldo positivo de R$ {saldo:,.2f}")
                    elif saldo < 0:
                        relatorio.append(f"⚠️ Saldo negativo de R$ {abs(saldo):,.2f}")
                    else:
                        relatorio.append("⚖️ Receitas e despesas equilibradas")
                    
                    if total_despesas > 0 and total_receitas > 0:
                        percentual = (total_despesas / total_receitas) * 100
                        relatorio.append(f"📊 Você gastou {percentual:.1f}% das suas receitas")
                    
                    parsed_response['assistant_message'] = "\n".join(relatorio)
                    parsed_response['report_generated'] = True
                    
                    logger_chat.info(f"📊 RELATÓRIO - Gerado com sucesso")
                    
                except Exception as e:
                    logger_chat.error(f"Erro ao gerar relatório: {e}")
                    parsed_response['assistant_message'] = f"⚠️ Erro ao gerar relatório: {str(e)}"
                    parsed_response['clarification_needed'] = True
            else:
                if needs_clarification:
                    logger_chat.info("📊 RELATÓRIO - Aguardando esclarecimento")

        # Salvar histórico do chat
        if request.user.is_authenticated:
            try:
                save_chat_history(
                    user=request.user,
                    user_message=message_text,
                    assistant_response=parsed_response.get('assistant_message', ''),
                    intent=intent,
                    transcribed_text=transcribed_text
                )
            except Exception as e:
                logger_chat.warning(f"Erro ao salvar histórico do chat: {e}")

        response_serializer = ChatResponseSerializer(data=parsed_response)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=rest_status.HTTP_200_OK)
        else:
            logger_chat.warning(f"Resposta da OpenAI não seguiu o schema esperado: {response_serializer.errors}")
            return Response(parsed_response, status=rest_status.HTTP_200_OK)

    except OpenAIClientError as exc:
        logger_chat.error(f"Erro do cliente OpenAI: {exc}")
        return Response(
            {
                "error": "Erro ao processar sua mensagem com o assistente.",
                "detail": str(exc)
            },
            status=rest_status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as exc:
        logger_chat.exception("Erro inesperado ao processar mensagem do chat")
        return Response(
            {
                "error": "Erro interno ao processar sua mensagem.",
                "detail": str(exc)
            },
            status=rest_status.HTTP_500_INTERNAL_SERVER_ERROR
        )

