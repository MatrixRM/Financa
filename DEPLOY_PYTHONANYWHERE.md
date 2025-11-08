# 🚀 Deploy no PythonAnywhere

## Pré-requisitos
1. Conta no PythonAnywhere (gratuita): https://www.pythonanywhere.com
2. Código no GitHub (opcional, mas recomendado)

## Passo 1: Criar conta e configurar

1. Acesse: https://www.pythonanywhere.com/registration/register/beginner/
2. Crie sua conta gratuita
3. Faça login no dashboard

## Passo 2: Upload do projeto

### Opção A: Via Git (Recomendado)
```bash
# No console Bash do PythonAnywhere
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd SEU_REPOSITORIO
```

### Opção B: Upload manual
1. Vá em "Files"
2. Faça upload do projeto zipado
3. Extraia os arquivos

## Passo 3: Criar ambiente virtual

```bash
# No console Bash do PythonAnywhere
cd ~/SEU_PROJETO
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Passo 4: Configurar variáveis de ambiente

Crie o arquivo `.env` no diretório do projeto:

```bash
nano .env
```

Cole o conteúdo:
```
SECRET_KEY=sua-secret-key-super-segura-aqui
DEBUG=False
ALLOWED_HOSTS=.pythonanywhere.com
DATABASE_URL=sqlite:///db.sqlite3
OPENAI_API_KEY=sua-chave-openai-aqui
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_TRANSCRIPTION_MODEL=whisper-1
```

Salve com `Ctrl+O`, `Enter`, `Ctrl+X`

## Passo 5: Preparar banco de dados

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

## Passo 6: Configurar Web App

1. Vá na aba **Web**
2. Clique em **Add a new web app**
3. Escolha **Manual configuration** (não Django)
4. Escolha **Python 3.10**

### Configurar WSGI

1. Clique no link do arquivo WSGI
2. Apague tudo e cole:

```python
import os
import sys

# Adicione o diretório do projeto ao path
path = '/home/SEU_USUARIO/SEU_PROJETO'
if path not in sys.path:
    sys.path.insert(0, path)

# Configurar variáveis de ambiente
os.environ['DJANGO_SETTINGS_MODULE'] = 'controle_despesas.settings'

# Ativar ambiente virtual
activate_this = '/home/SEU_USUARIO/SEU_PROJETO/venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# Carregar aplicação Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Configurar Virtualenv

1. Na aba **Web**, seção **Virtualenv**
2. Cole o caminho: `/home/SEU_USUARIO/SEU_PROJETO/venv`

### Configurar arquivos estáticos

Na seção **Static files**:
- URL: `/static/`
- Directory: `/home/SEU_USUARIO/SEU_PROJETO/staticfiles`

- URL: `/media/`
- Directory: `/home/SEU_USUARIO/SEU_PROJETO/media`

## Passo 7: Ajustes no settings.py

Certifique-se que `settings.py` tem:

```python
# Configurações para produção
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = ['seu-usuario.pythonanywhere.com', 'localhost', '127.0.0.1']

# HTTPS no PythonAnywhere
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG

# CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://seu-usuario.pythonanywhere.com',
]

# Static e Media
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

## Passo 8: Reload e teste

1. Clique no botão verde **Reload** no topo da página Web
2. Acesse: `https://seu-usuario.pythonanywhere.com`

## Passo 9: Funcionalidades especiais

### ⚠️ Microfone
- ✅ Funciona automaticamente (PythonAnywhere tem HTTPS)
- Não precisa configurar ngrok

### ✅ Biometria
- ✅ Funciona automaticamente (HTTPS nativo)

### 📊 Dashboard
- ✅ Todas as funcionalidades funcionam

## Troubleshooting

### Erro 500
1. Vá em **Web** > **Error log**
2. Leia os erros
3. Geralmente são:
   - Secret key não configurada
   - ALLOWED_HOSTS incorreto
   - Migrações não executadas

### Static files não carregam
```bash
python manage.py collectstatic --noinput
```
Depois clique em **Reload**

### Permissões de banco de dados
```bash
chmod 664 db.sqlite3
chmod 775 .
```

## Manutenção

### Atualizar código
```bash
cd ~/SEU_PROJETO
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```
Depois clique em **Reload** na aba Web

## 🎉 Pronto!

Seu sistema está online em: `https://seu-usuario.pythonanywhere.com`

### Links úteis:
- Dashboard PythonAnywhere: https://www.pythonanywhere.com/user/SEU_USUARIO/
- Documentação: https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/
- Console: https://www.pythonanywhere.com/user/SEU_USUARIO/consoles/
