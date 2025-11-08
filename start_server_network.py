#!/usr/bin/env python
"""
Script para iniciar o servidor Django com acesso pela rede local.
Exibe automaticamente o IP da máquina para facilitar o acesso de outros dispositivos.
"""

import socket
import subprocess
import sys
import os

def get_local_ip():
    """Obtém o IP local da máquina na rede"""
    try:
        # Cria um socket para descobrir o IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Não precisa realmente conectar, apenas configurar
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "Não foi possível obter o IP"

def print_access_info(ip, port=8000):
    """Exibe informações de acesso formatadas"""
    print("\n" + "="*60)
    print(" 🌐 SERVIDOR DJANGO RODANDO NA REDE LOCAL")
    print("="*60)
    print(f"\n📱 ACESSO DE OUTROS DISPOSITIVOS:")
    print(f"   → http://{ip}:{port}")
    print(f"\n💻 ACESSO LOCAL:")
    print(f"   → http://localhost:{port}")
    print(f"   → http://127.0.0.1:{port}")
    print("\n📋 INSTRUÇÕES:")
    print("   1. Certifique-se de que os dispositivos estão na mesma rede WiFi")
    print("   2. No seu celular/tablet, abra o navegador")
    print(f"   3. Digite o endereço: http://{ip}:{port}")
    print("   4. Faça login normalmente")
    print("\n⚠️  IMPORTANTE:")
    print("   - Seu firewall pode bloquear conexões externas")
    print("   - Se não funcionar, desative temporariamente o firewall")
    print("   - Este modo é apenas para desenvolvimento/rede local")
    print("\n🛑 Para parar o servidor: Pressione Ctrl+C")
    print("="*60 + "\n")

def main():
    # Obter IP local
    local_ip = get_local_ip()
    
    # Porta padrão
    port = 8000
    
    # Verificar se uma porta foi especificada
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("⚠️  Porta inválida. Usando porta padrão 8000.")
    
    # Exibir informações
    print_access_info(local_ip, port)
    
    # Executar o servidor Django
    try:
        # Verificar se estamos no diretório correto
        if not os.path.exists('manage.py'):
            print("❌ Erro: manage.py não encontrado!")
            print("   Execute este script do diretório raiz do projeto.")
            sys.exit(1)
        
        # Iniciar servidor
        print("🚀 Iniciando servidor...\n")
        subprocess.run([
            sys.executable,  # Python atual
            'manage.py',
            'runserver',
            f'0.0.0.0:{port}'  # 0.0.0.0 permite acesso externo
        ])
    except KeyboardInterrupt:
        print("\n\n✅ Servidor encerrado com sucesso!")
    except FileNotFoundError:
        print("\n❌ Erro: Não foi possível encontrar o Python ou manage.py")
        print("   Certifique-se de estar no diretório correto do projeto.")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")

if __name__ == "__main__":
    main()
