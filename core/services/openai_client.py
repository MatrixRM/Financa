import json
import re
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
                        "set_goal",
                        "check_goal",
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
                    "anyOf": [
                        {
                            "type": "object",
                            "description": "Dados de uma única transação.",
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
                        {
                            "type": "array",
                            "description": "Lista de múltiplas transações quando o usuário menciona várias compras.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["despesa", "receita"],
                                    },
                                    "amount": {
                                        "type": "number",
                                    },
                                    "title": {
                                        "type": "string",
                                    },
                                    "category": {
                                        "type": "string",
                                    },
                                    "account": {
                                        "type": "string",
                                    },
                                    "date": {
                                        "type": "string",
                                        "format": "date",
                                    },
                                    "notes": {
                                        "type": "string",
                                    },
                                },
                            },
                        },
                    ],
                    "description": "Dados estruturados da transação. Pode ser um objeto único ou array de múltiplas transações.",
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
                "goal": {
                    "type": "object",
                    "description": "Meta financeira quando o usuário quer definir ou consultar metas.",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["monthly_spending", "monthly_saving", "category_limit"],
                            "description": "Tipo de meta (limite mensal de gastos, meta de economia, limite por categoria).",
                        },
                        "amount": {
                            "type": "number",
                            "description": "Valor da meta em reais.",
                        },
                        "category": {
                            "type": "string",
                            "description": "Categoria específica se for limite por categoria.",
                        },
                        "period": {
                            "type": "string",
                            "description": "Período da meta (ex: 'dezembro 2025', 'este mês').",
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
            "Você deve decidir entre as ações: (1) NOVA TRANSAÇÃO, (2) EDITAR transação, (3) RELATÓRIO, (4) DEFINIR META, (5) CONSULTAR META.\n\n"

            "REGRAS PARA NOVAS TRANSAÇÕES (intent: create_transaction):\n"
            "- Reconheça gastos (paguei, comprei, gastei) como 'despesa'.\n"
            "- Reconheça entradas (recebi, entrou, salário) como 'receita'.\n"
            "- Valor sempre numérico e positivo.\n"
            "- Inferir categoria e conta quando possível.\n\n"
            
            "MÚLTIPLAS COMPRAS:\n"
            "- Se o usuário mencionar várias compras COM VALORES, retorne um ARRAY de transações.\n"
            "- CÁLCULO DE VALORES:\n"
            "  * 'N items de R$X' → valor UNITÁRIO = X, total = N × X\n"
            "  * '3 cervejas de R$5,50' → cada uma custa R$5,50 → total = 3 × 5,50 = 16,50\n"
            "  * '2 chocolates de R$3,50' → cada um custa R$3,50 → total = 2 × 3,50 = 7,00\n"
            "  * Exemplo: 'Comprei 3 salgados de R$5 e 2 refrigerantes de R$4'\n"
            "    → [{amount:15, title:'3 salgados'}, {amount:8, title:'2 refrigerantes'}]\n"
            "- Se faltar informação crítica (valor), marque 'clarification_needed': true.\n\n"
            
            "CONTEXTO E CORREÇÕES:\n"
            "- ANALISE O HISTÓRICO: Se o usuário acabou de registrar algo e agora está CORRIGINDO, use edit_transaction!\n"
            "- Frases de correção: 'o chocolate custa X', 'na verdade era Y', 'corrigi isso', 'era X não Y'\n"
            "- Frases de confirmação: 'é isso mesmo', 'está certo', 'correto', 'sim' → NÃO CRIE NOVA TRANSAÇÃO!\n"
            "  * Use intent='small_talk' e confirme: 'Ok, registrado!'\n"
            "- Exemplo de CORREÇÃO:\n"
            "  User: 'comprei 3 chocolates de R$13,50' → Você registra 3×13.50=40.50\n"
            "  User: 'o chocolate custa R$3,50 cada um' → Você EDITA com search_criteria={title:'chocolate'}, transaction={amount:10.50}\n"
            "- Exemplo de CONFIRMAÇÃO:\n"
            "  User: 'é esse o valor aí mesmo' → intent='small_talk', assistant_message='✅ Confirmado!'\n\n"

            "REGRAS PARA EDIÇÃO (intent: edit_transaction):\n"
            "- Verbos: editar, alterar, mudar, corrigir, atualizar.\n"
            "- search_criteria: dados para ENCONTRAR a transação.\n"
            "- transaction: apenas campos a ALTERAR.\n\n"

            "REGRAS DE DATA (CRÍTICO):\n"
            f"- SEM data informada = {hoje_iso}\n"
            f"- 'hoje', 'agora' = {hoje_iso}\n"
            f"- 'ontem' = {ontem_iso}\n"
            f"- 'amanhã' = {amanha_iso}\n\n"

            "REGRAS PARA RELATÓRIOS (intent: query_summary):\n"
            "- Palavras-chave: quanto gastei, total, relatório, extrato, resumo.\n"
            "- Inferir período: 'este mês' = mês atual, 'dezembro' = dezembro/2025.\n"
            "- Especificar summary_type: month_total (total do mês), category_total (por categoria), etc.\n"
            "- Se perguntar 'quanto gastei este mês', use: summary_type='month_total', type='despesa'.\n"
            "- Se perguntar sobre categoria específica, preencher 'category'.\n\n"

            "REGRAS PARA METAS (intent: set_goal ou check_goal):\n"
            "- set_goal: quando usuário quer DEFINIR uma meta (ex: 'quero gastar no máximo R$ 1500 este mês').\n"
            "- check_goal: quando usuário quer CONSULTAR meta existente (ex: 'estou dentro da meta?').\n"
            "- Tipos de meta:\n"
            "  * monthly_spending: limite total de gastos no mês\n"
            "  * monthly_saving: meta de economia no mês\n"
            "  * category_limit: limite para categoria específica\n"
            "- Exemplo: 'quero gastar no máximo 1500 este mês' → intent='set_goal', goal={type='monthly_spending', amount=1500}\n\n"

            "REGRAS PARA OUTROS CASOS:\n"
            "- greeting: saudações (oi, olá, bom dia) → responda com cumprimento amigável\n"
            "- small_talk: conversa casual → responda educadamente e direcione para finanças\n"
            "- unknown: quando não entender → SEMPRE peça educadamente por mais detalhes\n\n"

            "CRÍTICO - SEMPRE RESPONDA:\n"
            "- NUNCA deixe 'assistant_message' vazio\n"
            "- Se não entender, use intent='unknown' e peça esclarecimento\n"
            "- Se faltar informação, use 'clarification_needed': true e pergunte o que falta\n"
            "- SEMPRE seja educado e prestativo\n"
            "- SEMPRE responda algo, mesmo que não entenda perfeitamente\n\n"

            "PRINCÍPIOS GERAIS:\n"
            "- SEMPRE responda em JSON válido.\n"
            "- Use o contexto (histórico) para completar informações.\n"
            "- Respostas curtas do usuário geralmente são complementos da conversa anterior.\n"
            "- Seja proativo: se consegue inferir informação, faça.\n"
            "- NUNCA invente valores ou datas não mencionadas.\n"
            "- Seja claro e objetivo nas respostas.\n"
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
            # Limpar possíveis fences de Markdown e texto adicional.
            text = aggregated_text.strip()
            # Remover code fences ```json ``` e ```
            text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

            # Tentar extrair o primeiro objeto JSON completo ({ ... }) presente no texto.
            m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
            if m:
                return m.group(1).strip()

            # Se não encontrar objeto JSON, retornar o texto limpo para tentativa de parse.
            return text

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
            logger.debug(f"JSON COMPLETO da OpenAI: {json_payload}")
            parsed = json.loads(json_payload)
            
            # CORREÇÃO: Quando usa json_schema, o OpenAI retorna {"type":"object","properties":{...}}
            # Precisamos extrair apenas o conteúdo de "properties"
            if isinstance(parsed, dict) and parsed.get('type') == 'object' and 'properties' in parsed:
                logger.debug("🔧 Detectado formato json_schema, extraindo 'properties'")
                parsed = parsed['properties']
            
            # Validar que tem os campos obrigatórios
            if not parsed.get('intent'):
                logger.warning("Resposta sem 'intent', adicionando padrão")
                parsed['intent'] = 'unknown'
            
            if not parsed.get('assistant_message'):
                logger.warning("Resposta sem 'assistant_message', adicionando padrão")
                parsed['assistant_message'] = 'Desculpe, não consegui processar sua mensagem.'
            
            if 'clarification_needed' not in parsed:
                parsed['clarification_needed'] = False
            
            return parsed
            
        except json.JSONDecodeError as exc:
            logger.exception(f"JSON inválido da OpenAI: {exc}")
            logger.error(f"Conteúdo recebido: {json_payload if 'json_payload' in locals() else 'N/A'}")
            raise OpenAIClientError(
                "A resposta do modelo não pôde ser interpretada. Por favor, tente novamente."
            )
        except Exception as exc:
            logger.exception(f"Erro ao interpretar resposta da OpenAI: {exc}")
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
