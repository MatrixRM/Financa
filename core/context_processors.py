"""
Context processors para disponibilizar dados globalmente nos templates
"""
from .models import Categoria, Conta


def categorias_contas(request):
    """
    Adiciona categorias e contas ao contexto de todos os templates
    para uso no modal de transação rápida
    """
    if request.user.is_authenticated and hasattr(request.user, 'casa') and request.user.casa:
        categorias = Categoria.objects.filter(
            casa=request.user.casa,
            ativa=True
        ).order_by('tipo', 'nome')
        
        contas = Conta.objects.filter(
            casa=request.user.casa,
            ativa=True
        ).order_by('nome')
        
        return {
            'categorias': categorias,
            'contas': contas,
        }
    
    return {
        'categorias': [],
        'contas': [],
    }
