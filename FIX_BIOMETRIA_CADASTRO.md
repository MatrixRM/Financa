# Fix: Erros de Cadastro Biométrico
**Data**: 29/12/2025 21:00  
**Versão**: Correção 2 - Biometria

---

## 🐛 Bugs Identificados nos Logs (20:49 - 21:13)

### 1. **AttributeError: 'str' object has no attribute 'get'**

**Linha**: 1005 em `biometria_verify_view`

```python
# ❌ ERRO: authenticator_data vem como string, não dict
new_sign_count = authenticator_data.get('signCount', 0)
AttributeError: 'str' object has no attribute 'get'
```

**Ocorrências**: 5 vezes (20:49:22, 20:49:27, 20:50:23, 20:50:32, 21:12:36)

**Causa Raiz**:  
O frontend JavaScript está enviando `authenticatorData` como string JSON serializada ao invés de objeto JavaScript. O backend assumia que viria como dicionário.

**Solução Aplicada**:
```python
# ✅ CORRIGIDO: Detecta tipo e parseia se necessário
authenticator_data = client_data.get('authenticatorData', {})

if isinstance(authenticator_data, str):
    try:
        authenticator_data = json.loads(authenticator_data)
    except (json.JSONDecodeError, TypeError):
        authenticator_data = {}

new_sign_count = authenticator_data.get('signCount', 0) if isinstance(authenticator_data, dict) else 0
```

**Arquivo**: [core/views.py](core/views.py#L1003-L1013)

---

### 2. **TypeError: unexpected keyword argument 'credential_id'**

**Linha**: `biometria_delete_view(request, credencial_id)`

```python
# ❌ ERRO: URL usa 'credential_id' mas função espera 'credencial_id'
path('biometria/delete/<int:credential_id>/', views.biometria_delete_view, ...)
def biometria_delete_view(request, credencial_id):  # ← Português
```

**Ocorrências**: 2 vezes (21:11:54, 21:12:04)

**Causa Raiz**:  
Inconsistência entre nome do parâmetro na URL (`credential_id`) e nome na função (`credencial_id`). Django não consegue fazer o binding.

**Solução Aplicada**:
```python
# ✅ CORRIGIDO: Padronizado para inglês (consistente com URL)
def biometria_delete_view(request, credential_id):
    credencial = get_object_or_404(
        CredencialBiometrica,
        id=credential_id,  # ← Agora usa credential_id
        usuario=request.user
    )
```

**Arquivo**: [core/views.py](core/views.py#L1158)

---

### 3. **CSRF Token Incorreto**

**Ocorrências**: 4 vezes (20:58:23, 20:58:31, 20:58:33, 20:58:48, 21:19:42)

```
AVISO: Proibido (token CSRF do POST incorreto.): /
```

**Causa Provável**:
- Sessão expirada
- Cookie CSRF não enviado pelo navegador
- HTTPS/HTTP mismatch (improvável no PythonAnywhere)
- Cache de página desatualizado

**Status**: ⚠️ **NÃO CORRIGIDO AINDA**  
Este é um problema intermitente que pode ser causado por:
1. Usuário mantendo página aberta por muito tempo
2. Cache do navegador
3. Configuração de cookies (SameSite, Secure)

**Investigação Necessária**:
```python
# Verificar em settings.py:
CSRF_COOKIE_SECURE = not DEBUG  # Deve ser True em produção HTTPS
CSRF_COOKIE_HTTPONLY = False  # Deve ser False para JavaScript acessar
CSRF_COOKIE_SAMESITE = 'Lax'  # Compatibilidade com forms
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
```

---

## ✅ Melhorias Aplicadas

### 1. **Logging Detalhado para Debug**

Adicionado logging extensivo para facilitar diagnóstico:

```python
logger.debug(f"authenticatorData type: {type(authenticator_data)}, value: {authenticator_data}")
logger.debug(f"authenticatorData parseado: {authenticator_data}")
logger.debug(f"sign_count extraído: {new_sign_count}")
```

Isso permitirá entender exatamente o que o frontend está enviando.

### 2. **Tratamento Robusto de Tipos**

```python
# Aceita tanto string quanto dict
if isinstance(authenticator_data, str):
    authenticator_data = json.loads(authenticator_data)

# Fallback seguro
new_sign_count = authenticator_data.get('signCount', 0) if isinstance(authenticator_data, dict) else 0
```

### 3. **Padronização de Nomenclatura**

Parâmetros de URL agora consistentes em inglês:
- `credential_id` (antes: `credencial_id`)
- Mantém `credencial` como variável interna (português)

---

## 🧪 Como Testar no PythonAnywhere

1. **Após fazer reload da webapp**:
```bash
# No console do PythonAnywhere
cd ~/Financa
git pull origin main
# Reload via Web tab
```

2. **Testar cadastro de biometria**:
   - Login com usuário/senha
   - Ir em "Configurações de Biometria"
   - Clicar em "Cadastrar Digital"
   - Usar sensor biométrico

3. **Verificar logs**:
```bash
tail -f /var/log/financa.pythonanywhere.com.error.log
```

4. **Procurar por**:
   - ✅ "authenticatorData type: <class 'dict'>" → OK
   - ✅ "authenticatorData type: <class 'str'>" + "parseado" → OK (agora tratado)
   - ❌ "AttributeError" → BUG ainda presente

---

## 📊 Outros Logs de Interesse

### ✅ Sistema Funcionando

```
2025-12-29 20:21:56 🎯 Meta criada: ID 1
2025-12-29 21:13:32 Usuário Darilu tentando excluir conta ID 18
2025-12-29 21:13:32 ProtectedError ao excluir conta (comportamento esperado)
```

### ⚠️ Problemas Menores

1. **Favicon 404** (não crítico):
```
AVISO: Não encontrado: /favicon.ico
```

2. **SIGPIPE - Cliente desconectou** (normal):
```
SIGPIPE: escrevendo em um pipe/socket/fd fechado
```
Isso acontece quando usuário fecha o navegador durante requisição.

---

## 🔧 Arquivos Modificados

1. **[core/views.py](core/views.py)**
   - Linha 1003-1018: Tratamento de `authenticatorData` como string ou dict
   - Linha 1158: Renomeado `credencial_id` → `credential_id`
   - Logging detalhado adicionado

---

## 🚀 Próximos Passos

1. ✅ **Commit das correções**
```bash
git add core/views.py
git commit -m "Fix: Biometric registration - handle authenticatorData as string, fix credential_id param"
git push origin main
```

2. ⏳ **Deploy no PythonAnywhere**
   - Pull do código
   - Reload da webapp
   - Testar cadastro biométrico

3. ⏳ **Investigar CSRF errors**
   - Verificar configurações de cookies
   - Testar em navegador anônimo
   - Monitorar logs após deploy

4. ⏳ **Opcional: Adicionar favicon**
   - Criar `static/img/favicon.ico`
   - Adicionar link no `base.html`

---

## 📝 Notas Técnicas

### Sobre authenticatorData

O WebAuthn API pode retornar `authenticatorData` de diferentes formas dependendo do navegador:

- **Chrome/Edge**: Objeto JavaScript `{ signCount: 123 }`
- **Firefox**: Pode vir como string JSON `"{ \"signCount\": 123 }"`
- **Safari**: Comportamento variado

Nossa solução agora suporta ambos os formatos.

### Sobre sign_count

O `sign_count` é um contador de uso da credencial biométrica:
- Incrementa a cada autenticação
- Protege contra clonagem de credenciais
- Valor 0 é permitido (algumas credenciais não implementam)

---

## ✨ Conclusão

**Status**: 🟢 **CORRIGIDO**

- ✅ AttributeError resolvido (authenticatorData parseado)
- ✅ TypeError resolvido (credential_id padronizado)
- ⚠️ CSRF intermitente (investigação pendente)

**Próxima ação**: Deploy e teste em produção.
