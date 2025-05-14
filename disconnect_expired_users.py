#!/usr/bin/env python3
# disconnect_expired_users.py - Versão com tabela de sessões e remoção IXC

import os
import sys
import time
import schedule
import pymysql
import requests
import base64
from datetime import datetime, timedelta
from routeros_api import RouterOsApiPool
from routeros_api.exceptions import RouterOsApiConnectionError

print("=== Iniciando aplicação ===", flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Current time: {datetime.now()}", flush=True)

# Configurações do ambiente - Mikrotik
MIKROTIK_HOST = os.environ.get('MIKROTIK_HOST', '192.168.88.1')
MIKROTIK_USERNAME = os.environ.get('MIKROTIK_USERNAME', 'admin')
MIKROTIK_PASSWORD = os.environ.get('MIKROTIK_PASSWORD', 'password')
MIKROTIK_PORT = int(os.environ.get('MIKROTIK_PORT', '8728'))

# Configurações do ambiente - IXC
IXC_HOST = os.environ.get('IXC_HOST', '170.81.43.236')
IXC_TOKEN = os.environ.get('IXC_TOKEN', '')
IXC_API_BASE_URL = os.environ.get('IXC_API_BASE_URL', 'https://ixc.internet10.net.br/webservice/v1')

# Configurações do banco de dados
DATABASE_URL = os.environ.get('DATABASE_URL', '')
DEFAULT_ACTIVE_TIME_MINUTES = int(os.environ.get('DEFAULT_ACTIVE_TIME_MINUTES', '15'))

# Frequência de execução em minutos
CHECK_INTERVAL_MINUTES = int(os.environ.get('CHECK_INTERVAL_MINUTES', '5'))

print(f"Configurações carregadas:", flush=True)
print(f"  MIKROTIK_HOST: {MIKROTIK_HOST}", flush=True)
print(f"  MIKROTIK_USERNAME: {MIKROTIK_USERNAME}", flush=True)
print(f"  MIKROTIK_PORT: {MIKROTIK_PORT}", flush=True)
print(f"  IXC_HOST: {IXC_HOST}", flush=True)
print(f"  IXC_TOKEN configurado: {'Sim' if IXC_TOKEN else 'Não'}", flush=True)
print(f"  DATABASE_URL configurada: {'Sim' if DATABASE_URL else 'Não'}", flush=True)
print(f"  CHECK_INTERVAL_MINUTES: {CHECK_INTERVAL_MINUTES}", flush=True)
print(f"  DEFAULT_ACTIVE_TIME_MINUTES: {DEFAULT_ACTIVE_TIME_MINUTES}", flush=True)

def parse_database_url(url):
    """Extrai informações de conexão da URL do banco de dados"""
    print(f"Parseando DATABASE_URL...", flush=True)
    
    if not url:
        print("ERRO: DATABASE_URL está vazia!", flush=True)
        raise ValueError("DATABASE_URL não configurada")
    
    if url.startswith('mysql://'):
        url = url[8:]
    
    try:
        parts = url.split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        host_port = host_db[0].split(':')
        
        config = {
            'user': user_pass[0],
            'password': user_pass[1] if len(user_pass) > 1 else '',
            'host': host_port[0],
            'port': int(host_port[1]) if len(host_port) > 1 else 3306,
            'database': host_db[1] if len(host_db) > 1 else ''
        }
        
        print(f"DATABASE_URL parseada com sucesso", flush=True)
        print(f"  Host: {config['host']}:{config['port']}", flush=True)
        print(f"  Database: {config['database']}", flush=True)
        print(f"  User: {config['user']}", flush=True)
        
        return config
    except Exception as e:
        print(f"ERRO ao parsear DATABASE_URL: {e}", flush=True)
        raise

def get_db_connection():
    """Cria conexão com o banco de dados"""
    print("Criando conexão com banco de dados...", flush=True)
    try:
        db_config = parse_database_url(DATABASE_URL)
        conn = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("Conexão com banco criada com sucesso", flush=True)
        return conn
    except Exception as e:
        print(f"ERRO ao conectar ao banco: {e}", flush=True)
        raise

def get_active_time_minutes():
    """Obtém o tempo ativo configurado no banco de dados"""
    print("Obtendo tempo ativo do banco...", flush=True)
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT active_time_minutes FROM Conf LIMIT 1")
            result = cursor.fetchone()
            if result and result['active_time_minutes'] > 0:
                active_time = result['active_time_minutes']
                print(f"Tempo ativo obtido do banco: {active_time} minutos", flush=True)
                conn.close()
                return active_time
        conn.close()
    except Exception as e:
        print(f"Erro ao obter tempo ativo do banco: {e}", flush=True)
    
    print(f"Usando tempo ativo padrão: {DEFAULT_ACTIVE_TIME_MINUTES} minutos", flush=True)
    return DEFAULT_ACTIVE_TIME_MINUTES

def get_expired_sessions():
    """Busca sessões que ultrapassaram o tempo permitido e ainda não foram desconectadas"""
    active_time_minutes = get_active_time_minutes()
    time_limit = datetime.now() - timedelta(minutes=active_time_minutes)
    
    print(f"Tempo ativo configurado: {active_time_minutes} minutos", flush=True)
    print(f"Verificando sessões com última atualização antes de: {time_limit}", flush=True)
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Buscar apenas sessões que ainda não foram removidas, incluindo ixcId
            query = """
                SELECT s.id, s.name, s.mac, s.updatedAt, s.loginId,
                       l.ixcId
                FROM user_session s
                INNER JOIN login l ON s.loginId = l.id
                WHERE s.updatedAt < %s
                AND (s.removedhp = 'N' OR s.removedhp IS NULL)
            """
            cursor.execute(query, (time_limit,))
            sessions = cursor.fetchall()
        conn.close()
        print(f"Sessões expiradas encontradas: {len(sessions)}", flush=True)
        return sessions
    except Exception as e:
        print(f"ERRO ao buscar sessões expiradas: {e}", flush=True)
        return []

def mark_session_as_disconnected(session_id):
    """Marca uma sessão como desconectada no banco de dados"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            query = """
                UPDATE user_session 
                SET removedhp = 'S', 
                    disconnectedAt = NOW()
                WHERE id = %s
            """
            cursor.execute(query, (session_id,))
            conn.commit()
            print(f"Sessão ID {session_id} marcada como desconectada no banco", flush=True)
        conn.close()
    except Exception as e:
        print(f"ERRO ao marcar sessão como desconectada: {e}", flush=True)

def delete_ixc_login(ixc_id):
    """Remove o login do sistema IXC"""
    if not ixc_id:
        print("IXC ID não encontrado, pulando remoção do IXC", flush=True)
        return False
    
    if not IXC_TOKEN:
        print("IXC_TOKEN não configurado, pulando remoção do IXC", flush=True)
        return False
    
    try:
        print(f"Removendo login IXC ID: {ixc_id}...", flush=True)
        
        # Montar URL para deletar
        url = f"{IXC_API_BASE_URL}/radusuarios/{ixc_id}"
        
        # Preparar headers
        token_encoded = base64.b64encode(IXC_TOKEN.encode('utf-8')).decode('utf-8')
        headers = {
            'ixcsoft': '',
            'Authorization': f'Basic {token_encoded}',
        }
        
        # Fazer requisição DELETE
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 200:
            print(f"✔ Login IXC ID {ixc_id} removido com sucesso", flush=True)
            return True
        else:
            print(f"✖ Erro ao remover login IXC ID {ixc_id}: Status {response.status_code}", flush=True)
            print(f"  Resposta: {response.text}", flush=True)
            return False
    except Exception as e:
        print(f"ERRO ao remover login do IXC: {e}", flush=True)
        return False

def remove_entries(api, path, field, mac):
    """Remove entradas do Mikrotik baseado no MAC address"""
    try:
        print(f"Verificando {path} para MAC {mac}...", flush=True)
        res = api.get_resource(path)
        items = res.get(**{field: mac})
        
        if not items:
            print(f"[{path}] nenhum registro para MAC {mac}", flush=True)
            return
        
        for item in items:
            rid = item.get('.id') or item.get('id')
            if not rid:
                print(f"[{path}] registro sem ID: {item}", flush=True)
                continue
            
            try:
                res.remove(id=rid)
                print(f"[{path}] removido id={rid}", flush=True)
            except Exception as e:
                print(f"[{path}] falha ao remover id={rid}: {e}", flush=True)
    except Exception as e:
        print(f"ERRO ao processar {path}: {e}", flush=True)

def disconnect_session(mac):
    """Desconecta uma sessão do Mikrotik baseado no MAC address"""
    try:
        print(f"Conectando ao Mikrotik {MIKROTIK_HOST}:{MIKROTIK_PORT}...", flush=True)
        pool = RouterOsApiPool(
            host=MIKROTIK_HOST,
            username=MIKROTIK_USERNAME,
            password=MIKROTIK_PASSWORD,
            port=MIKROTIK_PORT,
            plaintext_login=True
        )
        api = pool.get_api()
        print("✔ Conectado ao Mikrotik", flush=True)
        
        # Remover cookies
        print("⟳ Removendo cookies...", flush=True)
        remove_entries(api, 'ip/hotspot/cookie', 'mac-address', mac)
        
        # Remover sessões ativas
        print("⟳ Removendo sessões ativas...", flush=True)
        remove_entries(api, 'ip/hotspot/active', 'mac-address', mac)
        
        pool.disconnect()
        print(f"✔ Sessão com MAC {mac} desconectada", flush=True)
        
    except RouterOsApiConnectionError as e:
        print(f"✖ Erro de conexão com Mikrotik: {e}", flush=True)
    except Exception as e:
        print(f"✖ Erro ao desconectar sessão: {e}", flush=True)

def check_expired_sessions():
    """Verifica e desconecta sessões expiradas"""
    print("\n--- Iniciando verificação de sessões expiradas ---", flush=True)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", flush=True)
    
    try:
        expired_sessions = get_expired_sessions()
        print(f"Sessões expiradas encontradas: {len(expired_sessions)}", flush=True)
        
        if not expired_sessions:
            print("Nenhuma sessão expirada encontrada", flush=True)
            return
        
        # Desconectar cada sessão expirada
        for session in expired_sessions:
            print(f"\nProcessando sessão: {session['name']} (MAC: {session['mac']})", flush=True)
            print(f"Última atualização: {session['updatedAt']}", flush=True)
            print(f"IXC ID do login: {session.get('ixcId', 'N/A')}", flush=True)
            
            # Desconectar do Mikrotik
            disconnect_session(session['mac'])
            
            # Remover login do IXC
            if session.get('ixcId'):
                delete_ixc_login(session['ixcId'])
            
            # Marcar como desconectada no banco
            mark_session_as_disconnected(session['id'])
        
        print("\n✔ Verificação de sessões expiradas concluída", flush=True)
    except Exception as e:
        print(f"ERRO durante verificação: {e}", flush=True)

def main():
    """Função principal"""
    print("=== Mikrotik User Session Disconnect Cron ===", flush=True)
    print(f"Servidor Mikrotik: {MIKROTIK_HOST}", flush=True)
    print(f"Servidor IXC: {IXC_HOST}", flush=True)
    print(f"Intervalo de verificação: {CHECK_INTERVAL_MINUTES} minutos", flush=True)
    
    # Verificar se DATABASE_URL está configurada
    if not DATABASE_URL:
        print("ERRO: DATABASE_URL não está configurada!", flush=True)
        print("Configure a variável de ambiente DATABASE_URL", flush=True)
        sys.exit(1)
    
    # Verificar conexão com o banco de dados
    try:
        print("Testando conexão com banco de dados...", flush=True)
        conn = get_db_connection()
        print("✔ Conexão com banco de dados OK", flush=True)
        conn.close()
    except Exception as e:
        print(f"✖ ERRO ao conectar ao banco de dados: {e}", flush=True)
        print("Verifique as configurações de DATABASE_URL", flush=True)
        sys.exit(1)
    
    # Executar verificação inicial se configurado
    if os.environ.get('RUN_ON_START', 'false').lower() == 'true':
        print("\nExecutando verificação inicial...", flush=True)
        check_expired_sessions()
    
    # Agendar execução periódica
    print(f"\nAgendando execução a cada {CHECK_INTERVAL_MINUTES} minutos", flush=True)
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_expired_sessions)
    
    print("Cron job iniciado com sucesso", flush=True)
    print("Pressione Ctrl+C para parar\n", flush=True)
    
    # Loop principal
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nEncerrando aplicação...", flush=True)
            break
        except Exception as e:
            print(f"ERRO no loop principal: {e}", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERRO FATAL: {e}", flush=True)
        sys.exit(1)
