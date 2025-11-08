from rest_framework import serializers
import json


class ChatMessageSerializer(serializers.Serializer):
    """Serializer para mensagens de chat do usuário."""

    message = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=5000,
        help_text="Mensagem de texto do usuário (obrigatória se não enviar áudio)"
    )
    audio = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="Arquivo de áudio para transcrição (obrigatório se não enviar mensagem)"
    )
    context = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="Histórico de conversa para manter contexto"
    )
    pending_transaction_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID da transação pendente de complemento/edição"
    )

    def validate_context(self, value):
        """Garante que context seja uma lista."""
        if not value:
            return []
        
        if isinstance(value, list):
            return value
        
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                return []
            except json.JSONDecodeError:
                return []
        
        return []

    def validate(self, data):
        """Valida que pelo menos uma forma de entrada foi fornecida."""
        message = data.get('message', '').strip()
        audio = data.get('audio')

        if not message and not audio:
            raise serializers.ValidationError(
                "Você deve fornecer uma mensagem de texto ou um arquivo de áudio."
            )

        return data


class ChatResponseSerializer(serializers.Serializer):
    """Serializer para resposta estruturada do assistente."""

    intent = serializers.CharField()
    clarification_needed = serializers.BooleanField()
    assistant_message = serializers.CharField()
    transaction = serializers.DictField(required=False, allow_null=True)
    query = serializers.DictField(required=False, allow_null=True)
    confidence = serializers.FloatField(required=False, allow_null=True)
    transcribed_text = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Texto transcrito do áudio enviado"
    )
    transaction_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID da transação criada/atualizada"
    )
    transaction_saved = serializers.BooleanField(
        required=False,
        help_text="Indica se a transação foi salva com sucesso"
    )
    transaction_pending = serializers.BooleanField(
        required=False,
        help_text="Indica se a transação está pendente de mais informações"
    )
