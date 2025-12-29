"""
Middleware de Rate Limiting para prote\u00e7\u00e3o contra abuse de APIs.
"""

from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
import hashlib
import time


class RateLimitMiddleware:
    """
    Middleware para limitar taxa de requisi\u00e7\u00f5es em endpoints sens\u00edveis.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Endpoints protegidos e seus limites
        self.rate_limits = {
            '/chat/message/': ('20/minute', 20, 60),  # 20 reqs por minuto
            '/biometria/challenge/': ('10/minute', 10, 60),
            '/biometria/verify/': ('5/minute', 5, 60),
            '/accounts/login/': ('5/minute', 5, 60),
            '/api/': ('100/minute', 100, 60),  # Limite gen\u00e9rico para APIs
        }
    
    def __call__(self, request):
        # Verificar se rate limiting est\u00e1 habilitado
        if not getattr(settings, 'RATE_LIMIT_ENABLED', False):
            return self.get_response(request)
        
        # Obter path da requisi\u00e7\u00e3o
        path = request.path
        
        # Verificar se \u00e9 um endpoint protegido
        limit_config = None
        for endpoint_pattern, config in self.rate_limits.items():
            if path.startswith(endpoint_pattern):
                limit_config = config
                break
        
        # Se n\u00e3o \u00e9 protegido, continuar normalmente
        if not limit_config:
            return self.get_response(request)
        
        # Extrair configura\u00e7\u00e3o
        _, max_requests, window_seconds = limit_config
        
        # Identificar cliente (IP + User-Agent + Path)
        client_id = self._get_client_id(request, path)
        
        # Verificar rate limit
        is_allowed, remaining, reset_time = self._check_rate_limit(
            client_id, max_requests, window_seconds
        )
        
        if not is_allowed:
            return JsonResponse({
                'error': 'Too many requests',
                'message': f'Rate limit exceeded. Try again in {int(reset_time - time.time())} seconds.',
                'retry_after': int(reset_time - time.time())
            }, status=429)
        
        # Adicionar headers de rate limit na resposta
        response = self.get_response(request)
        response['X-RateLimit-Limit'] = str(max_requests)
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Reset'] = str(int(reset_time))
        
        return response
    
    def _get_client_id(self, request, path):
        """Gera ID \u00fanico do cliente baseado em IP, User-Agent e Path."""
        # Obter IP (considerando proxies)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        # User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
        
        # Usu\u00e1rio autenticado (se houver)
        user_id = request.user.id if request.user.is_authenticated else 'anonymous'
        
        # Gerar hash
        client_string = f"{ip}:{user_agent}:{path}:{user_id}"
        return hashlib.sha256(client_string.encode()).hexdigest()[:16]
    
    def _check_rate_limit(self, client_id, max_requests, window_seconds):
        """
        Verifica se o cliente excedeu o rate limit.
        
        Retorna: (is_allowed, remaining_requests, reset_timestamp)
        """
        cache_key = f'ratelimit:{client_id}'
        
        # Obter dados do cache
        data = cache.get(cache_key, {'count': 0, 'reset': time.time() + window_seconds})
        
        current_time = time.time()
        
        # Se a janela expirou, resetar
        if current_time >= data['reset']:
            data = {'count': 0, 'reset': current_time + window_seconds}
        
        # Incrementar contador
        data['count'] += 1
        
        # Salvar no cache
        cache.set(cache_key, data, timeout=window_seconds)
        
        # Verificar se excedeu o limite
        is_allowed = data['count'] <= max_requests
        remaining = max(0, max_requests - data['count'])
        
        return is_allowed, remaining, data['reset']
