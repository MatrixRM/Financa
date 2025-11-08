# 💰 Controle de Despesas Domésticas

Sistema web completo para controle financeiro compartilhado com **Chat IA** integrado usando OpenAI.

## ✨ Destaques

- 🤖 **Chat Financeiro com IA** - Registre despesas conversando naturalmente
- 🎤 **Suporte a Áudio** - Grave mensagens de voz (Whisper AI)
- 📊 **Dashboard Interativo** - Gráficos em tempo real
- 🔐 **Autenticação Biométrica** - WebAuthn (impressão digital, Face ID)
- 📱 **Mobile-First** - Otimizado para celular
- 🏠 **Multiusuário** - Compartilhe despesas com sua casa

## 🚀 Tecnologias

- Django 5.0.2
- OpenAI API (GPT-4o-mini + Whisper)
- Django REST Framework
- PostgreSQL / SQLite
- Bootstrap 5
- Chart.js
- WebAuthn (Biometria)
- Python 3.12

## 📦 Instalação Local

### 1. Clone e configure ambiente

```bash
cd Financa
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 2. Instale dependências

```bash
pip install -r requirements.txt
```

### 3. Configure variáveis de ambiente

Crie um arquivo `.env` na raiz:

```env
SECRET_KEY=sua-secret-key-super-segura
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.*.*

# OpenAI (necessário para o chat)
OPENAI_API_KEY=sk-proj-...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_TRANSCRIPTION_MODEL=whisper-1

# Banco de dados (opcional - usa SQLite por padrão)
# DATABASE_URL=postgresql://usuario:senha@localhost:5432/financa_db
```

### 4. Execute migrações e crie superusuário

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 5. Inicie o servidor

**Para acesso local:**
```bash
python manage.py runserver
```

**Para acesso na rede (celular/tablet):**
```bash
python manage.py runserver 0.0.0.0:8000
```

### 6. Acesse o sistema

- Local: http://localhost:8000
- Rede: http://SEU_IP:8000

## 🌐 Deploy no PythonAnywhere

Para publicar gratuitamente com HTTPS (necessário para microfone e biometria):

📖 **Guia completo:** [DEPLOY_PYTHONANYWHERE.md](DEPLOY_PYTHONANYWHERE.md)

**Resumo:**
1. Crie conta em https://www.pythonanywhere.com
2. Faça upload ou clone o repositório
3. Configure ambiente virtual e `.env`
4. Execute migrações
5. Configure WSGI
6. Pronto! Seu app estará online com HTTPS

## 📱 Funcionalidades

### 🤖 Chat Financeiro (IA)
- ✅ Conversação natural para registrar transações
- ✅ Suporte a áudio (gravação de voz)
- ✅ Detecção automática de valores, categorias e datas
- ✅ Histórico completo de conversas
- ✅ Criação automática de contas e categorias

### 💰 Gestão Financeira
- ✅ Dashboard com gráficos interativos
- ✅ CRUD completo de transações
- ✅ Gerenciamento de contas bancárias
- ✅ Categorias personalizadas (ícones e cores)
- ✅ Relatórios e filtros avançados
- ✅ Divisão de despesas entre usuários

### 🔐 Segurança e UX
- ✅ Autenticação biométrica (WebAuthn)
- ✅ Login tradicional (usuário/senha)
- ✅ Casa compartilhada (multiusuário)
- ✅ Interface responsiva (mobile-first)
- ✅ Autocomplete e sugestões inteligentes
- ✅ Atalhos de teclado (Alt+N, Ctrl+S)

## 🎯 Como usar o Chat

### Exemplos de comandos:

**Registrar despesas:**
- "Gastei R$ 150 no supermercado"
- "Paguei R$ 80 de internet ontem"
- "Comprei remédio por R$ 35"

**Registrar receitas:**
- "Recebi R$ 5000 de salário"
- "Freelance me pagou R$ 800"

**Consultas:**
- "Quanto gastei este mês?"
- "Mostre minhas despesas de alimentação"
- "Qual meu saldo total?"

### 🎤 Áudio

- Clique no ícone do microfone 🎤
- Fale naturalmente
- Aguarde a transcrição e processamento
- ⚠️ **Requer HTTPS** (funciona em produção ou ngrok)

## 📊 Estrutura do Projeto

```
Financa/
├── manage.py
├── requirements.txt
├── .env                         # Variáveis de ambiente
├── controle_despesas/           # Configurações
│   ├── settings.py
│   └── urls.py
└── core/                        # App principal
    ├── models.py               # Modelos (Usuario, Casa, Conta, Transacao, etc)
    ├── views.py                # Views e lógica de negócio
    ├── urls.py                 # Rotas
    ├── forms.py                # Formulários
    ├── services/              
    │   └── openai_client.py    # Cliente OpenAI (chat + Whisper)
    ├── serializers/
    │   └── chat_serializers.py # Serializers da API de chat
    └── templates/              # Templates HTML
        ├── base.html
        ├── dashboard.html
        └── chat/
            └── interface.html   # Interface do chat
```

## 🔑 Variáveis de Ambiente

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `SECRET_KEY` | Chave secreta do Django | ✅ Sim |
| `DEBUG` | Modo debug (True/False) | ✅ Sim |
| `ALLOWED_HOSTS` | Hosts permitidos | ✅ Sim |
| `OPENAI_API_KEY` | Chave da OpenAI | ✅ Sim (chat) |
| `OPENAI_CHAT_MODEL` | Modelo GPT | Não (padrão: gpt-4o-mini) |
| `OPENAI_TRANSCRIPTION_MODEL` | Modelo Whisper | Não (padrão: whisper-1) |
| `DATABASE_URL` | URL do PostgreSQL | Não (usa SQLite) |

## 🛠️ Desenvolvimento

### Tecnologias e bibliotecas principais:

```txt
Django==5.0.2
djangorestframework==3.16.1
openai>=1.40.0
python-decouple==3.8
psycopg2-binary==2.9.10  # PostgreSQL
Pillow==11.0.0  # Imagens
reportlab==4.2.5  # PDF
```

### Comandos úteis:

```bash
# Executar testes
python manage.py test

# Criar nova migration
python manage.py makemigrations

# Ver SQL das migrations
python manage.py sqlmigrate core 0001

# Shell Django
python manage.py shell

# Limpar sessões expiradas
python manage.py clearsessions
```

## 🔐 Segurança

- ✅ Autenticação Django (passwords hasheadas)
- ✅ CSRF Protection
- ✅ Validações de formulário
- ✅ Proteção SQL Injection (ORM)
- ✅ HTTPS em produção (PythonAnywhere)
- ✅ WebAuthn para biometria
- ✅ Variáveis de ambiente para secrets

## 📄 Licença

MIT License - Use e modifique livremente!

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

## 📞 Suporte

- 📧 Email: seu-email@exemplo.com
- 🐛 Issues: GitHub Issues
- 📖 Docs: [DEPLOY_PYTHONANYWHERE.md](DEPLOY_PYTHONANYWHERE.md)

---

**Desenvolvido com ❤️ usando Django e OpenAI**
