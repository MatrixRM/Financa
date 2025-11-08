# 💰 Controle de Despesas Domésticas

Sistema web responsivo (mobile-first) para controle financeiro compartilhado entre duas pessoas.

## 🚀 Tecnologias

- Django 5.x
- Bootstrap 5
- Chart.js
- **PostgreSQL** (Recomendado) / SQLite
- Python 3.12

## 📦 Instalação

### Instalação Rápida (PostgreSQL - Recomendado)

1. **Clone o repositório e entre na pasta:**
```bash
cd Financa
```

2. **Crie um ambiente virtual:**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

4. **Instale e configure PostgreSQL:**

Baixe e instale: https://www.postgresql.org/download/windows/

Ou via gerenciador de pacotes:
```bash
# Chocolatey
choco install postgresql

# Scoop
scoop install postgresql
```

5. **Execute o setup automático do PostgreSQL:**
```bash
.\setup_postgresql.ps1
```

Este script irá:
- ✅ Criar o banco de dados `financa_db`
- ✅ Criar o usuário `financa_user`
- ✅ Configurar o arquivo `.env`
- ✅ Aplicar todas as migrações

6. **Crie um superusuário:**
```bash
python manage.py createsuperuser
```

7. **Execute o servidor:**

**Para acesso local apenas:**
```bash
python manage.py runserver
```

**Para acesso de outros dispositivos na rede (celular, tablet):**
```bash
# Windows - Opção 1 (mais fácil):
.\start_server_network.bat

# Windows - Opção 2:
.\start_server_network.ps1

# Python (qualquer OS):
python start_server_network.py

# Manual:
python manage.py runserver 0.0.0.0:8000
```

8. **Acesse:**
- Local: http://localhost:8000
- Rede: http://SEU_IP:8000 (veja o IP no terminal)

### 📚 Documentação Adicional

- � [Guia Completo PostgreSQL](MIGRACAO_POSTGRESQL.md)
- ⚡ [Guia Rápido PostgreSQL](POSTGRESQL_GUIA_RAPIDO.md)
- 📱 [Acesso via Rede Local](GUIA_ACESSO_REDE.md)
- 🎨 [Melhorias de Usabilidade](MELHORIAS_USABILIDADE.md)

## 📱 Funcionalidades

✅ Autenticação de usuários (login/registro)  
✅ Gerenciamento de Casa compartilhada (2 pessoas)  
✅ CRUD de Contas bancárias  
✅ CRUD de Categorias (despesas/receitas)  
✅ CRUD de Transações financeiras  
✅ Dashboard com gráficos interativos  
✅ Filtros avançados por período, categoria e conta  
✅ Exportação de relatórios (CSV e PDF)  
✅ Interface totalmente responsiva (mobile-first)  
✅ **Acesso pela rede local (celular, tablet, outros PCs)**  
✅ **Autocomplete inteligente de descrições**  
✅ **Formulário rápido de transação (modal)**  
✅ **Atalhos de teclado (Alt+N, Ctrl+S)**  
✅ **Sugestões baseadas em histórico**  
✅ Notificações visuais  
✅ Confirmações em modais  

📖 **Melhorias de Usabilidade:** Veja [MELHORIAS_USABILIDADE.md](MELHORIAS_USABILIDADE.md) para detalhes sobre as otimizações implementadas.

## 🎨 Interface

- **Mobile-first:** Design otimizado para smartphones
- **Bootstrap 5:** Interface moderna e responsiva
- **Chart.js:** Gráficos de pizza e barras
- **FAB Button:** Botão flutuante para adicionar transações rapidamente
- **Dark mode ready:** Preparado para modo escuro (opcional)

## 📊 Estrutura do Projeto

```
Financa/
├── manage.py
├── controle_despesas/          # Configurações do projeto
├── core/                       # App principal
│   ├── models.py              # Modelos de dados
│   ├── views.py               # Lógica das views
│   ├── forms.py               # Formulários
│   ├── urls.py                # URLs do app
│   ├── templates/             # Templates HTML
│   └── static/                # CSS, JS, imagens
└── requirements.txt
```

## 🔐 Segurança

- Senhas criptografadas (Django Auth)
- CSRF Protection
- Validações de formulário
- Proteção contra SQL Injection (ORM)

## 📄 Licença

MIT License - Sinta-se livre para usar e modificar!
