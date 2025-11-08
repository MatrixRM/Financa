# ✅ Checklist de Deploy - PythonAnywhere

## 📋 Informações Importantes

**SECRET_KEY para produção:**
```
&mazcu@v^%-fl#-78%7@rq$*zhbi6cx-we-x4qkay%%ks4&f$(
```

**OpenAI API Key:**
```
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
```

---

## Passo 1: Conta no PythonAnywhere ✅

- [ ] Criar conta em: https://www.pythonanywhere.com/registration/register/beginner/
- [ ] Fazer login no dashboard
- [ ] Anotar seu username: `_______________`

---

## Passo 2: Upload do Projeto

### Opção A: Via GitHub (Recomendado)

1. **Criar repositório no GitHub:**
   - [ ] Acesse: https://github.com/new
   - [ ] Nome do repositório: `controle-financas`
   - [ ] Marque como Private
   - [ ] Clique em "Create repository"

2. **Fazer push do código:**
   ```bash
   cd C:\Users\rober\Desktop\Financa
   git init
   git add .
   git commit -m "Deploy inicial - Sistema de Controle Financeiro"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/controle-financas.git
   git push -u origin main
   ```

3. **No PythonAnywhere:**
   - [ ] Abra um console Bash
   - [ ] Execute:
   ```bash
   git clone https://github.com/SEU_USUARIO/controle-financas.git
   cd controle-financas
   ```

### Opção B: Upload Manual

1. **Compactar projeto:**
   - [ ] Exclua pasta `venv/`
   - [ ] Compacte toda a pasta em `projeto.zip`

2. **No PythonAnywhere:**
   - [ ] Vá em "Files"
   - [ ] Clique em "Upload a file"
   - [ ] Faça upload do `projeto.zip`
   - [ ] No console Bash: `unzip projeto.zip`

---

## Passo 3: Configurar Ambiente Virtual

No console Bash do PythonAnywhere:

```bash
cd ~/controle-financas  # ou o nome da sua pasta
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Checklist:**
- [ ] Ambiente virtual criado
- [ ] Pip atualizado
- [ ] Todas as dependências instaladas (sem erros)

---

## Passo 4: Criar arquivo .env

No console Bash:

```bash
nano .env
```

Cole isto (CTRL+SHIFT+V):

```env
SECRET_KEY=&mazcu@v^%-fl#-78%7@rq$*zhbi6cx-we-x4qkay%%ks4&f$(
DEBUG=False
ALLOWED_HOSTS=.pythonanywhere.com
DATABASE_URL=sqlite:///db.sqlite3
OPENAI_API_KEY=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
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_TRANSCRIPTION_MODEL=whisper-1
```

Salve: `CTRL+O` → `Enter` → `CTRL+X`

**Checklist:**
- [ ] Arquivo .env criado
- [ ] Todas as variáveis configuradas

---

## Passo 5: Preparar Banco de Dados

```bash
python manage.py migrate
python manage.py createsuperuser
# Usuário: admin
# Email: seu@email.com
# Senha: (escolha uma senha forte)
python manage.py collectstatic --noinput
```

**Checklist:**
- [ ] Migrações aplicadas
- [ ] Superusuário criado
- [ ] Arquivos estáticos coletados

---

## Passo 6: Configurar Web App

1. **Criar Web App:**
   - [ ] Vá na aba "Web"
   - [ ] Clique "Add a new web app"
   - [ ] Next → Next
   - [ ] Escolha "Manual configuration"
   - [ ] Escolha "Python 3.10"
   - [ ] Next

2. **Configurar WSGI:**

Clique no link do arquivo WSGI (algo como `/var/www/seuusuario_pythonanywhere_com_wsgi.py`)

**APAGUE TUDO** e cole:

```python
import os
import sys

# Adicione o diretório do projeto
path = '/home/SEUUSUARIO/controle-financas'  # ⚠️ TROQUE SEUUSUARIO
if path not in sys.path:
    sys.path.insert(0, path)

# Configurar Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'controle_despesas.settings'

# Ativar ambiente virtual
activate_this = '/home/SEUUSUARIO/controle-financas/venv/bin/activate_this.py'  # ⚠️ TROQUE SEUUSUARIO
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# Carregar Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**⚠️ IMPORTANTE:** Troque `SEUUSUARIO` pelo seu username do PythonAnywhere!

**Checklist:**
- [ ] Arquivo WSGI configurado
- [ ] Username correto nos caminhos

3. **Configurar Virtualenv:**
   - [ ] Na aba "Web", seção "Virtualenv"
   - [ ] Clique em "Enter path to a virtualenv"
   - [ ] Cole: `/home/SEUUSUARIO/controle-financas/venv` (troque SEUUSUARIO)

4. **Configurar Arquivos Estáticos:**

Na seção "Static files", adicione:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/SEUUSUARIO/controle-financas/staticfiles` |
| `/media/` | `/home/SEUUSUARIO/controle-financas/media` |

**Checklist:**
- [ ] Virtualenv configurado
- [ ] Static files configurados
- [ ] Media files configurados

---

## Passo 7: Ajustar settings.py (se necessário)

Abra o arquivo `controle_despesas/settings.py` e verifique:

```python
# Deve ter estas linhas:
CSRF_TRUSTED_ORIGINS = [
    'https://seuusuario.pythonanywhere.com',  # ⚠️ TROQUE pelo seu domínio
]

# HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

Se não tiver, adicione antes de `INSTALLED_APPS`.

---

## Passo 8: Reload e Teste! 🚀

1. **Reload:**
   - [ ] Na aba "Web", clique no botão verde **"Reload"** no topo

2. **Teste:**
   - [ ] Acesse: `https://seuusuario.pythonanywhere.com`
   - [ ] Faça login
   - [ ] Teste o dashboard
   - [ ] Teste o chat (texto)
   - [ ] Teste o chat (microfone) 🎤
   - [ ] Teste a biometria 👆

---

## 🐛 Troubleshooting

### Erro 502 Bad Gateway
- Verifique o arquivo WSGI
- Certifique-se que os caminhos estão corretos
- Clique em "Reload"

### Erro 500
1. Vá em "Web" > "Error log"
2. Leia os erros
3. Geralmente é:
   - SECRET_KEY não configurada
   - ALLOWED_HOSTS incorreto
   - Migrações não executadas

### Static files não carregam
```bash
python manage.py collectstatic --noinput
```
Depois: Reload

### OpenAI não funciona
- Verifique se OPENAI_API_KEY está no .env
- Teste: `python manage.py shell`
```python
from core.services.openai_client import OpenAIClient
client = OpenAIClient()
print("✅ OpenAI configurado!")
```

---

## ✅ Deploy Concluído!

Seu sistema está online em: `https://seuusuario.pythonanywhere.com`

### 🎉 Funcionalidades Ativas:

- ✅ HTTPS nativo (seguro)
- ✅ Microfone funciona (Whisper AI)
- ✅ Chat com IA (GPT-4o-mini)
- ✅ Biometria (WebAuthn)
- ✅ Dashboard completo
- ✅ Acesso de qualquer lugar do mundo

---

## 📞 Suporte

- Documentação PythonAnywhere: https://help.pythonanywhere.com
- Django Docs: https://docs.djangoproject.com
- OpenAI API: https://platform.openai.com/docs
