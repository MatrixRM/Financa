import logging
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from core.models import Transacao, Conta, Categoria, ChatHistory
from core.serializers.chat_serializers import ChatMessageSerializer, ChatResponseSerializer
from core.services.openai_client import OpenAIClient, OpenAIClientError

logger = logging.getLogger('chat_views')


def save_chat_transaction(user, transaction_data, original_message, status='paga'):
    """Salva uma transação criada via chat no banco de dados."""
    from zoneinfo import ZoneInfo
    
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
    
    # Processar data
    tz_br = ZoneInfo('America/Sao_Paulo')
    date_str = transaction_data.get('date')
    if date_str:
        try:
            data_transacao = datetime.fromisoformat(date_str).date()
            logger.info(f"Data obtida da IA: {data_transacao}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao converter data '{date_str}': {e}. Usando data atual.")
            data_transacao = timezone.now().astimezone(tz_br).date()
    else:
        data_transacao = timezone.now().astimezone(tz_br).date()
        logger.info(f"Nenhuma data fornecida, usando data atual: {data_transacao}")
    
    # Criar a transação
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
    """Atualiza uma transação existente."""
    try:
        transacao = Transacao.objects.get(id=transaction_id, casa=user.casa)
    except Transacao.DoesNotExist:
        raise ValueError(f"Transação {transaction_id} não encontrada")
    
    if 'amount' in transaction_data:
        transacao.valor = Decimal(str(transaction_data['amount']))
    if 'title' in transaction_data:
        transacao.titulo = transaction_data['title']
    if 'type' in transaction_data:
        transacao.tipo = transaction_data['type']
    
    if 'category' in transaction_data:
        categoria, _ = Categoria.objects.get_or_create(
            casa=user.casa,
            nome=transaction_data['category'],
            defaults={'tipo': transacao.tipo, 'cor': '#6c757d', 'icone': '💰', 'ativa': True}
        )
        transacao.categoria = categoria
    
    if 'date' in transaction_data:
        try:
            transacao.data = datetime.fromisoformat(transaction_data['date']).date()
        except:
            pass
    
    transacao.save()
    logger.info(f"Transação {transaction_id} atualizada")
    return transacao


def search_transactions(user, criteria):
    """Busca transações baseado em critérios."""
    if not user.casa:
        return Transacao.objects.none()
    
    queryset = Transacao.objects.filter(casa=user.casa)
    
    if criteria.get('category'):
        queryset = queryset.filter(categoria__nome__icontains=criteria['category'])
    if criteria.get('date'):
        try:
            date_obj = datetime.fromisoformat(criteria['date']).date()
            queryset = queryset.filter(data=date_obj)
        except:
            pass
    if criteria.get('title_contains'):
        queryset = queryset.filter(titulo__icontains=criteria['title_contains'])
    
    return queryset.order_by('-data', '-id')[:10]


def save_chat_history(user, user_message, assistant_response, intent, transcribed_text=None):
    """Salva histórico da conversa."""
    ChatHistory.objects.create(
        usuario=user,
        user_message=user_message,
        assistant_response=assistant_response,
        intent=intent,
        transcribed_text=transcribed_text
    )


@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def chat_message_view(request):
    """Endpoint principal para processar mensagens do chat financeiro."""
    
    serializer = ChatMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data
    message_text = validated_data.get('message', '').strip()
    audio_file = validated_data.get('audio')
    context = validated_data.get('context', [])

    try:
        client = OpenAIClient()

        # Transcrever áudio se houver
        transcribed_text = None
        if audio_file:
            logger.info("Transcrevendo áudio...")
            transcribed_text = client.transcribe_audio(audio_file)
            message_text = transcribed_text
            logger.info(f"Áudio transcrito: {transcribed_text[:100]}...")

        if not message_text:
            return Response(
                {"error": "Mensagem vazia"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Processar mensagem
        logger.info(f"Processando: {message_text[:100]}...")
        parsed_response = client.parse_user_message(message=message_text, context=context)
        
        # Garantir que sempre há uma resposta válida
        if not parsed_response:
            logger.warning("OpenAI retornou resposta vazia")
            parsed_response = {
                'intent': 'unknown',
                'clarification_needed': False,
                'assistant_message': '😕 Desculpe, não consegui processar sua mensagem. Pode reformular?'
            }
        
        # Garantir que assistant_message existe
        if 'assistant_message' not in parsed_response or not parsed_response['assistant_message']:
            logger.warning("Resposta sem assistant_message, adicionando padrão")
            parsed_response['assistant_message'] = '🤔 Recebi sua mensagem, mas não tenho certeza do que fazer. Pode me dar mais detalhes?'
        
        # Garantir que intent existe
        if 'intent' not in parsed_response:
            parsed_response['intent'] = 'unknown'
        
        # Garantir que clarification_needed existe
        if 'clarification_needed' not in parsed_response:
            parsed_response['clarification_needed'] = False
        
        if transcribed_text:
            parsed_response['transcribed_text'] = transcribed_text

        intent = parsed_response.get('intent')
        needs_clarification = parsed_response.get('clarification_needed', False)
        
        # Log completo da resposta para debug
        logger.debug(f"🔍 RESPOSTA COMPLETA DA IA: {parsed_response}")

        # ===== CRIAR TRANSAÇÃO =====
        if intent == 'create_transaction' and not needs_clarification:
            transaction_data = parsed_response.get('transaction')
            
            logger.debug(f"🔍 TRANSACTION_DATA RECEBIDA: tipo={type(transaction_data)}, valor={transaction_data}")
            
            # Verificar se é array de transações ou uma única
            if isinstance(transaction_data, list):
                # Múltiplas transações
                logger.info(f"📦 Processando {len(transaction_data)} transações")
                transacoes_salvas = []
                
                if request.user.is_authenticated:
                    for idx, trans_data in enumerate(transaction_data):
                        if trans_data.get('amount'):
                            try:
                                transacao = save_chat_transaction(
                                    user=request.user,
                                    transaction_data=trans_data,
                                    original_message=f"{message_text} (item {idx+1})",
                                    status='paga'
                                )
                                transacoes_salvas.append(transacao)
                                logger.info(f"✅ Transação {idx+1} criada: ID {transacao.id}")
                            except Exception as e:
                                logger.error(f"❌ Erro na transação {idx+1}: {e}")
                    
                    if transacoes_salvas:
                        total = sum(t.valor for t in transacoes_salvas)
                        lista_itens = "\n".join([
                            f"  • {t.titulo}: R$ {t.valor:.2f}"
                            for t in transacoes_salvas
                        ])
                        
                        parsed_response['transaction_saved'] = True
                        parsed_response['transaction_ids'] = [t.id for t in transacoes_salvas]
                        parsed_response['assistant_message'] = (
                            f"✅ {len(transacoes_salvas)} despesas registradas!\n\n"
                            f"{lista_itens}\n\n"
                            f"💸 Total: R$ {total:.2f}"
                        )
                    else:
                        parsed_response['assistant_message'] = "⚠️ Não foi possível registrar as transações. Verifique os valores."
            
            elif isinstance(transaction_data, dict) and transaction_data.get('amount'):
                # Transação única
                if request.user.is_authenticated:
                    try:
                        transacao = save_chat_transaction(
                            user=request.user,
                            transaction_data=transaction_data,
                            original_message=message_text,
                            status='paga'
                        )
                        
                        tipo_emoji = "💸" if transacao.tipo == "despesa" else "💰"
                        parsed_response['transaction_saved'] = True
                        parsed_response['transaction_id'] = transacao.id
                        parsed_response['assistant_message'] = (
                            f"✅ {transacao.tipo.capitalize()} registrada!\n\n"
                            f"{tipo_emoji} R$ {transacao.valor:.2f}\n"
                            f"📝 {transacao.titulo}\n"
                            f"🏷️ {transacao.categoria.nome}\n"
                            f"🏦 {transacao.conta.nome}\n"
                            f"📅 {transacao.data.strftime('%d/%m/%Y')}"
                        )
                        logger.info(f"Transação criada: ID {transacao.id}")
                    except Exception as e:
                        logger.error(f"Erro ao salvar transação: {e}")
                        parsed_response['transaction_saved'] = False
                        parsed_response['assistant_message'] = f"⚠️ Erro ao salvar: {str(e)}"
            else:
                logger.warning("Dados de transação inválidos ou sem valor")
                if not parsed_response.get('assistant_message'):
                    parsed_response['assistant_message'] = "⚠️ Preciso saber o valor da compra para registrar."
                    parsed_response['clarification_needed'] = True

        # ===== EDITAR TRANSAÇÃO =====
        elif intent == 'edit_transaction' and not needs_clarification:
            search_criteria = parsed_response.get('search_criteria', {})
            transaction_data = parsed_response.get('transaction', {})
            
            if request.user.is_authenticated and search_criteria:
                try:
                    found = search_transactions(request.user, search_criteria)
                    
                    if found.count() == 1:
                        transacao = update_chat_transaction(
                            transaction_id=found.first().id,
                            user=request.user,
                            transaction_data=transaction_data,
                            original_message=message_text
                        )
                        parsed_response['transaction_saved'] = True
                        parsed_response['assistant_message'] = (
                            f"✅ Transação atualizada!\n\n"
                            f"📝 {transacao.titulo}\n"
                            f"💰 R$ {transacao.valor:.2f}\n"
                            f"📅 {transacao.data.strftime('%d/%m/%Y')}"
                        )
                    elif found.count() == 0:
                        parsed_response['assistant_message'] = "❌ Nenhuma transação encontrada."
                        parsed_response['clarification_needed'] = True
                    else:
                        trans_list = "\n".join([
                            f"  {i+1}. {t.data.strftime('%d/%m')} - {t.titulo} - R$ {t.valor:.2f}"
                            for i, t in enumerate(found[:5])
                        ])
                        parsed_response['assistant_message'] = (
                            f"🔍 Encontrei {found.count()} transações:\n\n{trans_list}\n\n"
                            "Seja mais específico (data, valor exato)."
                        )
                        parsed_response['clarification_needed'] = True
                except Exception as e:
                    logger.error(f"Erro ao editar: {e}")
                    parsed_response['assistant_message'] = f"⚠️ Erro: {str(e)}"

        # ===== RELATÓRIOS =====
        elif intent == 'query_summary' and not needs_clarification:
            query = parsed_response.get('query', {})
            logger.info(f"📊 Gerando relatório: {query}")
            
            if request.user.is_authenticated:
                try:
                    # Definir período
                    hoje = datetime.now().date()
                    period = query.get('period', {})
                    
                    if period.get('start_date') and period.get('end_date'):
                        inicio = datetime.fromisoformat(period['start_date']).date()
                        fim = datetime.fromisoformat(period['end_date']).date()
                    else:
                        # Mês atual por padrão
                        inicio = hoje.replace(day=1)
                        if hoje.month == 12:
                            fim = hoje.replace(day=31)
                        else:
                            proximo = hoje.replace(month=hoje.month + 1, day=1)
                            fim = proximo - timedelta(days=1)
                    
                    logger.info(f"📊 Período: {inicio} a {fim}")
                    
                    # Buscar transações
                    queryset = Transacao.objects.filter(
                        casa=request.user.casa,
                        data__gte=inicio,
                        data__lte=fim
                    )
                    
                    category_filter = query.get('category')
                    if category_filter:
                        queryset = queryset.filter(categoria__nome__icontains=category_filter)
                    
                    type_filter = query.get('type')
                    if type_filter and type_filter != 'todas':
                        queryset = queryset.filter(tipo=type_filter)
                    
                    # Calcular totais
                    despesas_agg = queryset.filter(tipo='despesa').aggregate(
                        total=Sum('valor'), count=Count('id')
                    )
                    receitas_agg = queryset.filter(tipo='receita').aggregate(
                        total=Sum('valor'), count=Count('id')
                    )
                    
                    total_despesas = despesas_agg['total'] or 0
                    total_receitas = receitas_agg['total'] or 0
                    saldo = total_receitas - total_despesas
                    
                    # Top categorias
                    top_despesas = queryset.filter(tipo='despesa').values(
                        'categoria__nome'
                    ).annotate(
                        total=Sum('valor'), count=Count('id')
                    ).order_by('-total')[:5]
                    
                    # Montar relatório
                    periodo_texto = f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
                    
                    relatorio = [
                        "📊 **RELATÓRIO FINANCEIRO**",
                        f"📅 Período: {periodo_texto}",
                        "",
                        "💰 **RESUMO**",
                        f"• Receitas: R$ {total_receitas:,.2f} ({receitas_agg['count']} transações)",
                        f"• Despesas: R$ {total_despesas:,.2f} ({despesas_agg['count']} transações)",
                        f"• Saldo: R$ {saldo:,.2f}",
                        ""
                    ]
                    
                    if top_despesas:
                        relatorio.append("📉 **TOP 5 DESPESAS**")
                        for item in top_despesas:
                            cat = item['categoria__nome'] or 'Outros'
                            relatorio.append(f"• {cat}: R$ {item['total']:,.2f}")
                        relatorio.append("")
                    
                    # Análise
                    if saldo > 0:
                        relatorio.append(f"✅ Saldo positivo de R$ {saldo:,.2f}")
                    elif saldo < 0:
                        relatorio.append(f"⚠️ Saldo negativo de R$ {abs(saldo):,.2f}")
                    else:
                        relatorio.append("⚖️ Receitas e despesas equilibradas")
                    
                    if total_receitas > 0:
                        percentual = (total_despesas / total_receitas) * 100
                        relatorio.append(f"📊 Você gastou {percentual:.1f}% das receitas")
                    
                    parsed_response['assistant_message'] = "\n".join(relatorio)
                    parsed_response['report_generated'] = True
                    logger.info("📊 Relatório gerado com sucesso")
                    
                except Exception as e:
                    logger.error(f"Erro no relatório: {e}")
                    parsed_response['assistant_message'] = f"⚠️ Erro ao gerar relatório: {str(e)}"

        # ===== DEFINIR META =====
        elif intent == 'set_goal' and not needs_clarification:
            goal_data = parsed_response.get('goal', {})
            logger.info(f"🎯 Definindo meta: {goal_data}")
            
            if request.user.is_authenticated and goal_data.get('amount'):
                try:
                    from core.models import Meta as MetaFinanceira
                    
                    # Extrair dados
                    tipo_meta = goal_data.get('type', 'monthly_spending')
                    valor_meta = Decimal(str(goal_data['amount']))
                    
                    # Determinar mês/ano
                    hoje = datetime.now().date()
                    mes = hoje.month
                    ano = hoje.year
                    
                    # Buscar ou criar categoria se necessário
                    categoria_meta = None
                    if tipo_meta == 'category_limit' and goal_data.get('category'):
                        categoria_meta, _ = Categoria.objects.get_or_create(
                            casa=request.user.casa,
                            nome=goal_data['category'],
                            defaults={'tipo': 'despesa', 'cor': '#6c757d', 'icone': '🎯', 'ativa': True}
                        )
                    
                    # Criar ou atualizar meta
                    meta, criada = MetaFinanceira.objects.update_or_create(
                        casa=request.user.casa,
                        tipo=tipo_meta,
                        categoria=categoria_meta,
                        mes=mes,
                        ano=ano,
                        defaults={
                            'valor': valor_meta,
                            'criada_por': request.user,
                            'ativa': True
                        }
                    )
                    
                    tipo_texto = dict(MetaFinanceira.TIPO_META_CHOICES).get(tipo_meta, 'Meta')
                    periodo_texto = f"{mes}/{ano}"
                    
                    if criada:
                        parsed_response['assistant_message'] = (
                            f"✅ Meta definida com sucesso!\n\n"
                            f"🎯 {tipo_texto}\n"
                            f"💰 R$ {valor_meta:,.2f}\n"
                            f"📅 Período: {periodo_texto}"
                        )
                    else:
                        parsed_response['assistant_message'] = (
                            f"✅ Meta atualizada!\n\n"
                            f"🎯 {tipo_texto}\n"
                            f"💰 R$ {valor_meta:,.2f} (novo valor)\n"
                            f"📅 Período: {periodo_texto}"
                        )
                    
                    parsed_response['goal_set'] = True
                    logger.info(f"🎯 Meta {'criada' if criada else 'atualizada'}: ID {meta.id}")
                    
                except Exception as e:
                    logger.error(f"Erro ao definir meta: {e}")
                    parsed_response['assistant_message'] = f"⚠️ Erro ao definir meta: {str(e)}"

        # ===== CONSULTAR META =====
        elif intent == 'check_goal':
            logger.info("🎯 Consultando metas")
            
            if request.user.is_authenticated:
                try:
                    from core.models import Meta as MetaFinanceira
                    
                    # Buscar metas ativas do mês atual
                    hoje = datetime.now().date()
                    metas = MetaFinanceira.objects.filter(
                        casa=request.user.casa,
                        mes=hoje.month,
                        ano=hoje.year,
                        ativa=True
                    )
                    
                    if not metas.exists():
                        parsed_response['assistant_message'] = (
                            "📊 Você ainda não definiu metas para este mês.\n\n"
                            "💡 Dica: Diga 'quero gastar no máximo R$ 1500 este mês' para definir uma meta!"
                        )
                    else:
                        # Calcular gastos do mês
                        inicio_mes = hoje.replace(day=1)
                        gastos_mes = Transacao.objects.filter(
                            casa=request.user.casa,
                            tipo='despesa',
                            data__gte=inicio_mes,
                            data__lte=hoje
                        ).aggregate(total=Sum('valor'))['total'] or 0
                        
                        relatorio_metas = ["🎯 **SUAS METAS**\n"]
                        
                        for meta in metas:
                            tipo_texto = dict(MetaFinanceira.TIPO_META_CHOICES).get(meta.tipo)
                            percentual = (gastos_mes / meta.valor * 100) if meta.valor > 0 else 0
                            
                            status_emoji = "✅" if percentual <= 100 else "⚠️"
                            
                            relatorio_metas.append(
                                f"{status_emoji} {tipo_texto}\n"
                                f"   Meta: R$ {meta.valor:,.2f}\n"
                                f"   Gasto: R$ {gastos_mes:,.2f} ({percentual:.1f}%)\n"
                                f"   Restante: R$ {(meta.valor - gastos_mes):,.2f}\n"
                            )
                        
                        parsed_response['assistant_message'] = "\n".join(relatorio_metas)
                        parsed_response['goal_checked'] = True
                        
                except Exception as e:
                    logger.error(f"Erro ao consultar metas: {e}")
                    parsed_response['assistant_message'] = f"⚠️ Erro ao consultar metas: {str(e)}"

        # ===== CASOS NÃO TRATADOS (greeting, small_talk, unknown) =====
        # Se chegou aqui e não tem mensagem, fornecer resposta padrão
        if not parsed_response.get('assistant_message'):
            if intent == 'greeting':
                parsed_response['assistant_message'] = (
                    "👋 Olá! Eu sou seu assistente financeiro.\n\n"
                    "Posso ajudar você a:\n"
                    "• Registrar despesas e receitas\n"
                    "• Consultar seus gastos\n"
                    "• Definir e acompanhar metas\n"
                    "• Gerar relatórios\n\n"
                    "Como posso ajudar?"
                )
            elif intent == 'small_talk':
                parsed_response['assistant_message'] = (
                    "😊 Obrigado pela mensagem! Estou aqui para ajudar com suas finanças.\n\n"
                    "O que você gostaria de fazer?"
                )
            elif intent == 'unknown':
                parsed_response['assistant_message'] = (
                    "❓ Desculpe, não entendi sua solicitação.\n\n"
                    "Você pode:\n"
                    "• Registrar gastos: 'Gastei 50 reais no mercado'\n"
                    "• Ver relatórios: 'Quanto gastei este mês?'\n"
                    "• Definir metas: 'Quero gastar no máximo 1500 este mês'\n\n"
                    "Como posso ajudar?"
                )
            else:
                # Fallback para qualquer outro caso
                parsed_response['assistant_message'] = (
                    "🤔 Recebi sua mensagem.\n\n"
                    "Precisa de ajuda com despesas, receitas ou relatórios?"
                )

        # Salvar histórico
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
                logger.warning(f"Erro ao salvar histórico: {e}")

        # Validar resposta antes de retornar
        response_serializer = ChatResponseSerializer(data=parsed_response)
        if response_serializer.is_valid():
            logger.info(f"✅ Resposta enviada: intent={intent}, clarification={needs_clarification}")
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.warning(f"⚠️ Schema inválido: {response_serializer.errors}")
            logger.warning(f"Dados recebidos: {parsed_response}")
            # Retornar mesmo assim, mas com aviso
            return Response(parsed_response, status=status.HTTP_200_OK)

    except OpenAIClientError as exc:
        logger.error(f"❌ Erro OpenAI: {exc}")
        return Response(
            {
                "intent": "unknown",
                "clarification_needed": False,
                "assistant_message": "🔌 Erro ao conectar com o assistente. Por favor, tente novamente.",
                "error": str(exc)
            },
            status=status.HTTP_200_OK  # Retornar 200 para o frontend não quebrar
        )
    except Exception as exc:
        logger.exception("❌ Erro inesperado no chat")
        return Response(
            {
                "intent": "unknown",
                "clarification_needed": False,
                "assistant_message": "⚠️ Ocorreu um erro inesperado. Por favor, tente novamente.",
                "error": str(exc)
            },
            status=status.HTTP_200_OK  # Retornar 200 para o frontend não quebrar
        )


@api_view(['GET'])
def chat_interface_view(request):
    """
    Renderiza a interface de chat (HTML simples para teste).
    """
    from django.shortcuts import render
    return render(request, 'chat/interface.html')


@api_view(['GET'])
def chat_history_view(request):
    """Retorna o histórico recente de conversas do chat."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Usuário não autenticado"},
            status=status.HTTP_401_UNAUTHORIZED
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
    }, status=status.HTTP_200_OK)
