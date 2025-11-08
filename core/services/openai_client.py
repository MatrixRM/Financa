import json
import logging
from datetime import datetime, timedelta
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
                        "edit_transaction",
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
                "search_criteria": {
                    "type": "object",
                    "description": "Critérios de busca quando o usuário quer editar uma transação existente.",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Nome da categoria da transação a editar.",
                        },
                        "account": {
                            "type": "string",
                            "description": "Nome da conta da transação a editar.",
                        },
                        "date": {
                            "type": "string",
                            "format": "date",
                            "description": "Data da transação a editar (ISO YYYY-MM-DD).",
                        },
                        "min_amount": {
                            "type": "number",
                            "description": "Valor mínimo para busca.",
                        },
                        "max_amount": {
                            "type": "number",
                            "description": "Valor máximo para busca.",
                        },
                        "title_contains": {
                            "type": "string",
                            "description": "Palavras que devem estar no título/descrição.",
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
        tz_br = ZoneInfo('America/Sao_Paulo')
        hoje_dt = datetime.now(tz_br)
        hoje = hoje_dt.strftime("%d/%m/%Y")
        hoje_iso = hoje_dt.strftime("%Y-%m-%d")
        ontem_iso = (hoje_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        amanha_iso = (hoje_dt + timedelta(days=1)).strftime('%Y-%m-%d')

        return (
            f"Você é um assistente financeiro em português do Brasil. Data atual: {hoje} (ISO: {hoje_iso}). "
            "Seu trabalho é interpretar mensagens naturais do usuário sobre finanças pessoais e SEMPRE responder em JSON seguindo o schema fornecido. "
            "Você deve decidir entre três ações: (1) registrar uma NOVA TRANSAÇÃO, (2) EDITAR uma transação existente, ou (3) criar um PEDIDO DE RELATÓRIO.\n\n"

            "REGRAS PARA NOVAS TRANSAÇÕES (intent: create_transaction):\n"
            "- Reconheça frases que indiquem gasto (ex: paguei, comprei, gastei) como 'despesa'.\n"
            "- Reconheça frases que indiquem entrada (ex: recebi, entrou, salário) como 'receita'.\n"
            "- O valor deve ser sempre numérico e positivo.\n"
            "- Inferir categoria e conta quando possível, com base no contexto.\n"
            "- Se o usuário der informações insuficientes (valor, descrição, etc.), marque 'clarification_needed': true.\n\n"

            "REGRAS PARA EDIÇÃO DE TRANSAÇÕES (intent: edit_transaction):\n"
            "- Reconheça verbos como: editar, alterar, mudar, corrigir, atualizar, modificar.\n"
            "- Preencha 'search_criteria' com os dados mencionados para ENCONTRAR a transação (categoria, data, conta, valor aproximado).\n"
            "- Preencha 'transaction' APENAS com os campos que o usuário quer ALTERAR (novo valor, nova categoria, etc.).\n"
            "- Exemplo: 'Edite a transação de pintura para 350 reais' → search_criteria: {category: 'pintura'}, transaction: {amount: 350}\n"
            "- Se faltar informação para localizar a transação, marque 'clarification_needed': true e pergunte detalhes (data, conta, etc.).\n\n"

            "REGRAS DE DATA (CRÍTICO):\n"
            f"- Se o usuário NÃO informar data, use OBRIGATORIAMENTE: {hoje_iso}.\n"
            f"- Se disser 'hoje', 'agora', 'agorinha', use SEMPRE: {hoje_iso}.\n"
            f"- 'Ontem' = {ontem_iso}.\n"
            f"- 'Amanhã' = {amanha_iso}.\n"
            "- Datas específicas devem ser convertidas para ISO (YYYY-MM-DD).\n"
            "- Nunca invente datas além dessas regras.\n\n"

            "REGRAS PARA RELATÓRIOS (intent: query_summary):\n"
            "- Quando identificado pedido de resumo, extrato, total do mês, total por categoria, etc., preencha o campo 'query'.\n"
            "- Especifique o tipo de relatório e o período, se puder inferir.\n\n"

            "PRINCÍPIOS GERAIS:\n"
            "- NUNCA retorne nada fora do formato JSON.\n"
            "- NUNCA inclua explicações fora do JSON.\n"
            "- Não adivinhe informações críticas.\n"
            "- Trabalhe sempre com base na data fornecida acima.\n"
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
