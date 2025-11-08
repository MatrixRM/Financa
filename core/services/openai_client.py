import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from django.conf import settings

try:
    from openai import OpenAI  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - dependência opcional em testes
    OpenAI = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class OpenAIClientError(Exception):
    """Erro genérico para problemas ao conversar com a API da OpenAI."""


class OpenAIClient:
    """Wrapper responsável por centralizar as chamadas à API da OpenAI."""

    _STRUCTURED_RESPONSE_SCHEMA: Dict[str, Any] = {
        "name": "finance_assistant_schema",
        "schema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "create_transaction",
                        "query_summary",
                        "greeting",
                        "clarification",
                        "small_talk",
                        "unknown",
                    ],
                    "description": "Ação principal inferida da mensagem do usuário.",
                },
                "clarification_needed": {
                    "type": "boolean",
                    "description": "Marque como verdadeiro quando for preciso pedir mais detalhes antes de executar qualquer ação.",
                },
                "assistant_message": {
                    "type": "string",
                    "description": "Resposta em português que será exibida para o usuário.",
                },
                "transaction": {
                    "type": "object",
                    "description": "Dados estruturados da transação quando o usuário informa um novo lançamento.",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["despesa", "receita"],
                            "description": "Defina como 'despesa' quando for gasto e 'receita' quando for ganho.",
                        },
                        "amount": {
                            "type": "number",
                            "description": "Valor numérico em reais. Deve sempre ser positivo.",
                        },
                        "currency": {
                            "type": "string",
                            "description": "Moeda informada pelo usuário (ex: BRL).",
                        },
                        "title": {
                            "type": "string",
                            "description": "Descrição curta da transação.",
                        },
                        "category": {
                            "type": "string",
                            "description": "Categoria principal sugerida para o lançamento.",
                        },
                        "account": {
                            "type": "string",
                            "description": "Conta sugerida (ex: cartão, conta corrente).",
                        },
                        "date": {
                            "type": "string",
                            "format": "date",
                            "description": "Data no formato ISO (YYYY-MM-DD).",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Observações adicionais relevantes.",
                        },
                    },
                    "additionalProperties": False,
                },
                "query": {
                    "type": "object",
                    "description": "Parâmetros quando o usuário solicita relatórios ou consultas.",
                    "properties": {
                        "summary_type": {
                            "type": "string",
                            "enum": [
                                "month_total",
                                "category_total",
                                "period_total",
                                "list_transactions",
                                "balance",
                            ],
                            "description": "Tipo de relatório solicitado.",
                        },
                        "category": {
                            "type": "string",
                            "description": "Nome da categoria alvo quando aplicável.",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["despesa", "receita", "todas"],
                            "description": "Filtrar por tipo de transação se especificado.",
                        },
                        "period": {
                            "type": "object",
                            "description": "Faixa de datas caso o usuário especifique um período.",
                            "properties": {
                                "start_date": {
                                    "type": "string",
                                    "format": "date",
                                },
                                "end_date": {
                                    "type": "string",
                                    "format": "date",
                                },
                            },
                            "additionalProperties": False,
                        },
                    },
                    "additionalProperties": False,
                },
                "confidence": {
                    "type": "number",
                    "description": "Grau de confiança da interpretação, variando entre 0 e 1.",
                },
            },
            "required": [
                "intent",
                "clarification_needed",
                "assistant_message",
            ],
            "additionalProperties": False,
        },
    }

    def _get_system_prompt(self) -> str:
        """Retorna o prompt do sistema com a data atual."""
        # Usar timezone brasileiro para garantir data correta
        tz_br = ZoneInfo('America/Sao_Paulo')
        hoje = datetime.now(tz_br).strftime("%d/%m/%Y")
        hoje_iso = datetime.now(tz_br).strftime("%Y-%m-%d")
        return (
            f"Você é um assistente financeiro em português. IMPORTANTE: A data de HOJE é {hoje} (ISO: {hoje_iso}). "
            "Sua missão é interpretar mensagens livres de usuários sobre finanças pessoais, "
            "identificar se o texto descreve um NOVO LANÇAMENTO (gasto ou receita) ou um PEDIDO DE RELATÓRIO. "
            "Responda SEMPRE em JSON seguindo o schema fornecido. "
            "Quando o usuário informar um gasto, defina 'type' como 'despesa'. Para ganhos, utilize 'receita'. "
            "Use valores positivos e tente inferir a categoria e a conta com base na descrição. "
            f"CRÍTICO: Quando a data NÃO for informada pelo usuário, você DEVE usar OBRIGATORIAMENTE a data de HOJE: {hoje_iso} no formato ISO. "
            f"Se o usuário disser 'hoje', 'agora', ou não mencionar data específica, use SEMPRE: {hoje_iso}. "
            f"Se disser 'ontem', calcule um dia antes de {hoje_iso}. Para 'amanhã', calcule um dia depois de {hoje_iso}. "
            "NUNCA invente datas. Use sempre a data fornecida neste prompt como referência. "
            "Se houver dúvida relevante (valor, categoria), marque 'clarification_needed' como true e peça os dados faltantes na resposta. "
            "Para pedidos de relatório, preencha o objeto 'query' com o tipo adequado e período, se possível."
        )

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise OpenAIClientError(
                "Variável OPENAI_API_KEY não configurada. Defina a chave da OpenAI no arquivo .env."
            )

        if OpenAI is None:
            raise OpenAIClientError(
                "Biblioteca 'openai' não instalada. Execute 'pip install openai'."
            )

        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._chat_model = settings.OPENAI_CHAT_MODEL
        self._transcription_model = settings.OPENAI_TRANSCRIPTION_MODEL

    def _extract_json_payload(self, raw_response: Any) -> str:
        """Tenta extrair o texto JSON das diferentes formas de resposta do SDK."""

        aggregated_text = ""

        # Para chat.completions.create()
        choices = getattr(raw_response, "choices", None)
        if not choices and isinstance(raw_response, dict):
            choices = raw_response.get("choices")

        if choices and len(choices) > 0:
            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            if message is None and isinstance(first_choice, dict):
                message = first_choice.get("message")
            
            if message:
                content = getattr(message, "content", None)
                if content is None and isinstance(message, dict):
                    content = message.get("content")
                
                if isinstance(content, str):
                    aggregated_text = content
                elif isinstance(content, list):
                    for item in content:
                        text_value = getattr(item, "text", None)
                        if text_value is None and isinstance(item, dict):
                            text_value = item.get("text")
                        if text_value:
                            aggregated_text += str(text_value)

        if aggregated_text:
            return aggregated_text

        raise ValueError("Não foi possível extrair o texto do JSON retornado pela OpenAI.")

    def parse_user_message(
        self,
        message: str,
        context: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Envia mensagem do usuário para o modelo e retorna JSON estruturado."""

        context = context or []

        input_messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": self._get_system_prompt(),
            }
        ]

        for item in context:
            input_messages.append(
                {
                    "role": item.get("role", "assistant"),
                    "content": item.get("content", ""),
                }
            )

        input_messages.append(
            {
                "role": "user",
                "content": message,
            }
        )

        try:
            response = self._client.chat.completions.create(
                model=self._chat_model,
                messages=input_messages,
                temperature=0.2,
                max_tokens=800,
                response_format={
                    "type": "json_schema",
                    "json_schema": self._STRUCTURED_RESPONSE_SCHEMA,
                },
            )
        except Exception as exc:  # pragma: no cover - dependente da API externa
            logger.exception("Falha ao chamar a OpenAI: %s", exc)
            raise OpenAIClientError("Erro ao se comunicar com a OpenAI. Tente novamente em instantes.")

        try:
            json_payload = self._extract_json_payload(response)
            return json.loads(json_payload)
        except Exception as exc:  # pragma: no cover - validação
            logger.exception("Erro ao interpretar JSON retornado pela OpenAI: %s", exc)
            raise OpenAIClientError(
                "A resposta do modelo não pôde ser interpretada. Por favor, tente novamente."
            )

    def transcribe_audio(self, file_obj) -> str:
        """Transcreve áudio enviado pelo usuário usando Whisper."""

        try:
            # O OpenAI SDK precisa de um objeto file-like com nome
            # Se for um InMemoryUploadedFile do Django, precisamos wrappear
            if hasattr(file_obj, 'read'):
                # Garantir que estamos no início do arquivo
                file_obj.seek(0)
                
                # Criar uma tupla (nome_do_arquivo, conteúdo, tipo_mime)
                file_name = getattr(file_obj, 'name', 'audio.webm')
                file_content = file_obj.read()
                
                # Criar um objeto BytesIO para passar para a API
                import io
                audio_file = io.BytesIO(file_content)
                audio_file.name = file_name
                
                transcription = self._client.audio.transcriptions.create(
                    model=self._transcription_model,
                    file=audio_file,
                    response_format="text",
                )
            else:
                # Se já for um objeto file normal
                transcription = self._client.audio.transcriptions.create(
                    model=self._transcription_model,
                    file=file_obj,
                    response_format="text",
                )
            
            if hasattr(transcription, "text"):
                return transcription.text.strip()
            return str(transcription).strip()
        except Exception as exc:  # pragma: no cover - dependente da API externa
            logger.exception("Erro ao transcrever áudio: %s", exc)
            raise OpenAIClientError(
                "Não foi possível transcrever o áudio enviado. Tente novamente ou digite a mensagem."
            )
