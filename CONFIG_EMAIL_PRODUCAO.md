# Configuração de Email no PythonAnywhere

## ⚠️ Problema Identificado nos Logs

```
smtplib.SMTPSenderRefused: (530, 'Authentication required')
from_addr='webmaster@localhost'
```

**Causa**: Email SMTP não está configurado no PythonAnywhere. Quando usuário tenta redefinir senha, o Django tenta enviar email mas falha.

---

## ✅ Solução Aplicada

### 1. **Console Backend Automático**

O código agora detecta automaticamente se o email está configurado:

- **SEM configuração**: Usa `console.EmailBackend` (emails aparecem no log, mas não são enviados)
- **COM configuração**: Usa `smtp.EmailBackend` (envia emails reais)

### 2. **Configurar Gmail no PythonAnywhere**

No arquivo `.env` do PythonAnywhere, adicione:

```bash
# Email Configuration (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu_email@gmail.com
EMAIL_HOST_PASSWORD=sua_senha_de_app
DEFAULT_FROM_EMAIL=seu_email@gmail.com
```

### 3. **Criar Senha de App no Gmail**

1. Acesse: https://myaccount.google.com/apppasswords
2. Selecione "Outro (nome personalizado)"
3. Digite: "Finança App - PythonAnywhere"
4. Clique em "Gerar"
5. Copie a senha de 16 caracteres
6. Cole no `EMAIL_HOST_PASSWORD`

---

## 🔧 Alternativa: Desabilitar Redefinição de Senha

Se não quiser configurar email, você pode:

### Opção A: Usar Console Backend (padrão agora)
Emails serão impressos no log ao invés de enviados.

### Opção B: Desabilitar a URL
Em `controle_despesas/urls.py`, comente:

```python
# path('redefinir-senha/', auth_views.PasswordResetView.as_view(...), name='password_reset'),
```

### Opção C: Redefinir senha via console

```bash
python manage.py changepassword nome_usuario
```

---

## 📊 Status Atual

✅ **Código corrigido**: Console backend ativo quando email não configurado  
✅ **Sem mais erros 500**: Redefinição funciona localmente (imprime no console)  
⏳ **PythonAnywhere**: Necessita configuração do Gmail ou alternativa acima

---

## 🧪 Testar no PythonAnywhere

1. **Sem configuração de email** (padrão):
   - Usuário clica em "Esqueci minha senha"
   - Django imprime email no log (não envia)
   - Verificar em: `/var/log/financa.pythonanywhere.com.error.log`

2. **Com Gmail configurado**:
   - Usuário recebe email real com link de redefinição
   - Email enviado de `seu_email@gmail.com`

---

## 🔗 Links Úteis

- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [Django Email Backend](https://docs.djangoproject.com/en/5.0/topics/email/)
- [PythonAnywhere Email Setup](https://help.pythonanywhere.com/pages/EmailSetup/)
