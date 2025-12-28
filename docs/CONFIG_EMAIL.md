# Configuração de Email Real no PythonAnywhere

## Passo 1: Criar Senha de App no Gmail

1. Acesse: https://myaccount.google.com/apppasswords
2. Faça login na sua conta Gmail
3. Digite um nome (ex: "Django Financa")
4. Clique em "Criar"
5. Copie a senha gerada (16 caracteres sem espaços)

## Passo 2: Configurar no PythonAnywhere

1. No console do PythonAnywhere, edite o arquivo `.env`:
```bash
cd ~/seuusuario.pythonanywhere.com
nano .env
```

2. Adicione estas linhas (substituindo pelos seus dados):
```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu_email@gmail.com
EMAIL_HOST_PASSWORD=sua_senha_de_app_de_16_caracteres
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=seu_email@gmail.com
```

3. Salve (Ctrl+O, Enter, Ctrl+X)

## Passo 3: Recarregar o Site

1. Vá na aba "Web" do PythonAnywhere
2. Clique no botão verde "Reload"

## Testar

Acesse `/redefinir-senha/` e teste com um email válido.
O email será enviado para o endereço cadastrado do usuário.

## Alternativa: SendGrid (se Gmail não funcionar no PythonAnywhere)

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=sua_api_key_sendgrid
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=seu_email_verificado@dominio.com
```

## Se der erro de rede no PythonAnywhere Free

Contas gratuitas do PythonAnywhere bloqueiam SMTP externo.
Você precisará:
- Atualizar para conta paga ($5/mês), ou
- Usar console backend (emails aparecem no log)
