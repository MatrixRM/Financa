import logging
from typing import Dict, Any

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from core.serializers.chat_serializers import ChatMessageSerializer, ChatResponseSerializer
from core.services.openai_client import OpenAIClient, OpenAIClientError

logger = logging.getLogger(__name__)


@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def chat_message_view(request):
    """
    Endpoint principal para processar mensagens do chat financeiro.
    
    Aceita texto ou áudio, envia para a OpenAI e retorna resposta estruturada.
    """

    serializer = ChatMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
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
            logger.info("Transcrevendo áudio do usuário...")
            transcribed_text = client.transcribe_audio(audio_file)
            message_text = transcribed_text
            logger.info(f"Áudio transcrito: {transcribed_text[:100]}...")

        if not message_text:
            return Response(
                {"error": "Não foi possível obter texto da mensagem ou transcrição."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Processa a mensagem com o modelo
        logger.info(f"Processando mensagem: {message_text[:100]}...")
        parsed_response = client.parse_user_message(
            message=message_text,
            context=context
        )

        # Adiciona o texto transcrito na resposta se houver
        if transcribed_text:
            parsed_response['transcribed_text'] = transcribed_text

        # Se a intenção for criar transação e não precisar de esclarecimento
        intent = parsed_response.get('intent')
        needs_clarification = parsed_response.get('clarification_needed', False)

        if intent == 'create_transaction' and not needs_clarification:
            transaction_data = parsed_response.get('transaction')
            if transaction_data:
                # Aqui você implementará a lógica de salvar no banco
                # Por enquanto, apenas registra no log
                logger.info(f"Transação a ser salva: {transaction_data}")
                # TODO: Implementar salvamento no banco de dados
                # created_transaction = save_transaction(transaction_data, request.user)
                # parsed_response['transaction_id'] = created_transaction.id

        response_serializer = ChatResponseSerializer(data=parsed_response)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.warning(f"Resposta da OpenAI não seguiu o schema esperado: {response_serializer.errors}")
            return Response(parsed_response, status=status.HTTP_200_OK)

    except OpenAIClientError as exc:
        logger.error(f"Erro do cliente OpenAI: {exc}")
        return Response(
            {
                "error": "Erro ao processar sua mensagem com o assistente.",
                "detail": str(exc)
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as exc:
        logger.exception("Erro inesperado ao processar mensagem do chat")
        return Response(
            {
                "error": "Erro interno ao processar sua mensagem.",
                "detail": str(exc)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
