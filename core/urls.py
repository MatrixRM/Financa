from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Autenticação
    path('', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('casa/', views.casa_detalhes_view, name='casa_detalhes'),

    # Redefinição de senha (Password reset)
    path('redefinir-senha/',
         auth_views.PasswordResetView.as_view(
             template_name='auth/password_reset_form.html',
             email_template_name='auth/password_reset_email.html',
             success_url=reverse_lazy('password_reset_done')
         ),
         name='password_reset'),
    path('redefinir-senha/enviado/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='auth/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('redefinir-senha/confirmar/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='auth/password_reset_confirm.html',
             success_url=reverse_lazy('password_reset_complete')
         ),
         name='password_reset_confirm'),
    path('redefinir-senha/concluido/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='auth/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Contas
    path('contas/', views.conta_list_view, name='conta_list'),
    path('contas/criar/', views.conta_create_view, name='conta_create'),
    path('contas/<int:pk>/editar/', views.conta_update_view, name='conta_update'),
    path('contas/<int:pk>/excluir/', views.conta_delete_view, name='conta_delete'),
    
    # Categorias
    path('categorias/', views.categoria_list_view, name='categoria_list'),
    path('categorias/criar/', views.categoria_create_view, name='categoria_create'),
    path('categorias/<int:pk>/editar/', views.categoria_update_view, name='categoria_update'),
    path('categorias/<int:pk>/excluir/', views.categoria_delete_view, name='categoria_delete'),
    
    # Transações
    path('transacoes/', views.transacao_list_view, name='transacao_list'),
    path('transacoes/criar/', views.transacao_create_view, name='transacao_create'),
    path('transacoes/<int:pk>/editar/', views.transacao_update_view, name='transacao_update'),
    path('transacoes/<int:pk>/excluir/', views.transacao_delete_view, name='transacao_delete'),
    
    # Relatórios
    path('relatorios/', views.relatorios_view, name='relatorios'),
    path('exportar/csv/', views.exportar_csv_view, name='exportar_csv'),
    path('exportar/pdf/', views.exportar_pdf_view, name='exportar_pdf'),
    
    # Biometria
    path('biometria/challenge/', views.biometria_challenge_view, name='biometria_challenge'),
    path('biometria/verify/', views.biometria_verify_view, name='biometria_verify'),
    path('biometria/register/', views.biometria_register_view, name='biometria_register'),
    path('biometria/settings/', views.biometria_settings_view, name='biometria_settings'),
    path('biometria/delete/<int:credential_id>/', views.biometria_delete_view, name='biometria_delete'),
    
    # Chat Financeiro
    path('chat/', views.chat_interface_view, name='chat_interface'),
    path('chat/message/', views.chat_message_view, name='chat_message'),
    path('chat/history/', views.chat_history_view, name='chat_history'),
]
