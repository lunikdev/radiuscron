#!/usr/bin/env python3
# test_connection.py

import os
from routeros_api import RouterOsApiPool
from routeros_api.exceptions import RouterOsApiConnectionError

# Configurações do Mikrotik
MIKROTIK_HOST = os.environ.get('MIKROTIK_HOST', '192.168.88.1')
MIKROTIK_USERNAME = os.environ.get('MIKROTIK_USERNAME', 'admin')
MIKROTIK_PASSWORD = os.environ.get('MIKROTIK_PASSWORD', 'password')
MIKROTIK_PORT = int(os.environ.get('MIKROTIK_PORT', '8728'))

def test_connection():
    """Testa conexão com o Mikrotik"""
    print("=== Teste de Conexão Mikrotik ===")
    print(f"Host: {MIKROTIK_HOST}")
    print(f"Porta: {MIKROTIK_PORT}")
    print(f"Usuário: {MIKROTIK_USERNAME}")
    print()
    
    try:
        print("Tentando conectar...")
        pool = RouterOsApiPool(
            host=MIKROTIK_HOST,
            username=MIKROTIK_USERNAME,
            password=MIKROTIK_PASSWORD,
            port=MIKROTIK_PORT,
            plaintext_login=True
        )
        api = pool.get_api()
        print("✔ Conectado com sucesso!")
        
        # Obter informações do sistema
        res = api.get_resource('/system/identity')
        identity = res.get()
        print(f"Sistema: {identity[0]['name']}")
        
        # Listar sessões ativas do hotspot
        res = api.get_resource('/ip/hotspot/active')
        active_sessions = res.get()
        print(f"\nSessões ativas no hotspot: {len(active_sessions)}")
        
        if active_sessions:
            print("\nPrimeiras 5 sessões:")
            for i, session in enumerate(active_sessions[:5]):
                print(f"{i+1}. MAC: {session.get('mac-address')}, "
                      f"User: {session.get('user')}, "
                      f"IP: {session.get('address')}")
        
        pool.disconnect()
        print("\n✔ Conexão fechada com sucesso")
        
    except RouterOsApiConnectionError as e:
        print(f"✖ Erro de conexão: {e}")
        print("\nPossíveis causas:")
        print("1. O IP do Mikrotik está incorreto")
        print("2. A API do Mikrotik não está habilitada")
        print("3. A porta da API está incorreta")
        print("4. Firewall bloqueando a conexão")
        print("5. Usuário ou senha incorretos")
    except Exception as e:
        print(f"✖ Erro: {e}")

if __name__ == "__main__":
    test_connection()