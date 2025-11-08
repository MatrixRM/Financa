from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Casa, Conta, Categoria, Transacao, ChatHistory


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Admin customizado para Usuario"""
    list_display = ['username', 'email', 'first_name', 'last_name', 'casa', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'casa']
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Adicionais', {'fields': ('casa', 'telefone', 'foto_perfil')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informações Adicionais', {'fields': ('casa', 'telefone', 'foto_perfil')}),
    )


@admin.register(Casa)
class CasaAdmin(admin.ModelAdmin):
    """Admin para Casa"""
    list_display = ['nome', 'codigo_convite', 'criada_em', 'qtd_membros']
    search_fields = ['nome', 'codigo_convite']
    readonly_fields = ['criada_em', 'codigo_convite']
    
    def qtd_membros(self, obj):
        return obj.membros.count()
    qtd_membros.short_description = 'Membros'


@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    """Admin para Conta"""
    list_display = ['nome', 'tipo', 'casa', 'saldo_inicial', 'ativa', 'criada_em']
    list_filter = ['tipo', 'ativa', 'casa']
    search_fields = ['nome', 'casa__nome']
    readonly_fields = ['criada_em']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """Admin para Categoria"""
    list_display = ['nome', 'tipo', 'casa', 'icone', 'cor', 'ativa']
    list_filter = ['tipo', 'ativa', 'casa']
    search_fields = ['nome', 'casa__nome']


@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    """Admin para Transacao"""
    list_display = ['titulo', 'tipo', 'valor', 'data', 'categoria', 'conta', 'status', 'pago_por']
    list_filter = ['tipo', 'status', 'data', 'categoria', 'conta', 'casa']
    search_fields = ['titulo', 'observacao']
    readonly_fields = ['criada_em', 'atualizada_em']
    date_hierarchy = 'data'
    filter_horizontal = ['dividido_entre']


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    """Admin para Histórico de Chat"""
    list_display = ['usuario', 'intent', 'created_at', 'get_short_message']
    list_filter = ['intent', 'created_at', 'usuario']
    search_fields = ['user_message', 'assistant_response', 'transcribed_text']
    readonly_fields = ['usuario', 'user_message', 'assistant_response', 'intent', 'transcribed_text', 'created_at']
    date_hierarchy = 'created_at'
    
    def get_short_message(self, obj):
        """Retorna os primeiros 50 caracteres da mensagem do usuário"""
        return obj.user_message[:50] + '...' if len(obj.user_message) > 50 else obj.user_message
    get_short_message.short_description = 'Mensagem'
    
    def has_add_permission(self, request):
        """Desabilita a adição manual de histórico"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Desabilita a edição de histórico"""
        return False

