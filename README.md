# Mikrotik User Disconnect Cron - Python (EasyPanel)

Este projeto Python funciona como um cron job para verificar usuários expirados e desconectá-los automaticamente do Mikrotik Hotspot.

## Deploy no EasyPanel

### Opção 1: Usando Template Python

1. **Criar novo App no EasyPanel**:
   - Clique em "New App"
   - Escolha "Python" como template
   - Conecte seu repositório GitHub

2. **Configurar variáveis de ambiente**:
   ```
   DATABASE_URL=mysql://user:pass@host:3306/database
   MIKROTIK_HOST=192.168.88.1
   MIKROTIK_USERNAME=admin
   MIKROTIK_PASSWORD=senha
   MIKROTIK_PORT=8728
   CHECK_INTERVAL_MINUTES=5
   DEFAULT_ACTIVE_TIME_MINUTES=15
   RUN_ON_START=false
   ```

3. **Build Settings**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python disconnect_expired_users.py`

### Opção 2: Usando Dockerfile

1. Use o Dockerfile incluído no projeto
2. No EasyPanel, selecione "Docker" como build type
3. Configure as mesmas variáveis de ambiente

## Arquivos do Projeto

- `disconnect_expired_users.py` - Script principal
- `requirements.txt` - Dependências Python
- `Dockerfile` - Para deploy via Docker
- `README.md` - Esta documentação

## Variáveis de Ambiente

- `DATABASE_URL`: URL completa de conexão MySQL
- `MIKROTIK_HOST`: IP do Mikrotik
- `MIKROTIK_USERNAME`: Usuário do Mikrotik
- `MIKROTIK_PASSWORD`: Senha do Mikrotik
- `MIKROTIK_PORT`: Porta da API (padrão: 8728)
- `CHECK_INTERVAL_MINUTES`: Intervalo de verificação em minutos (padrão: 5)
- `DEFAULT_ACTIVE_TIME_MINUTES`: Tempo padrão de sessão (padrão: 15)
- `RUN_ON_START`: Se "true", executa verificação ao iniciar

## Como Funciona

1. Conecta ao banco de dados MySQL
2. Verifica usuários cujo `updatedAt` ultrapassou o tempo configurado
3. Para cada usuário expirado:
   - Conecta ao Mikrotik via API
   - Remove cookies do hotspot
   - Remove sessões ativas
4. Repete o processo no intervalo configurado

## Logs

O sistema gera logs detalhados:
```
=== Mikrotik User Disconnect Cron ===
✔ Conexão com banco de dados OK
Agendando execução a cada 5 minutos
Cron job iniciado com sucesso

--- Iniciando verificação de usuários expirados ---
Usuários expirados encontrados: 2
Processando usuário: João Silva (MAC: AA:BB:CC:DD:EE:FF)
✔ Usuário desconectado
```

## Teste Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar com verificação inicial
RUN_ON_START=true python disconnect_expired_users.py
```

## Troubleshooting

### Erro de conexão com Mikrotik

1. Verifique se a API está habilitada no Mikrotik
2. Confirme usuário e senha
3. Verifique se a porta 8728 está acessível

### Erro de banco de dados

1. Verifique o formato da DATABASE_URL
2. Confirme que o banco está acessível
3. Verifique permissões do usuário

### Usuários não são desconectados

1. Verifique os logs para ver se foram encontrados
2. Confirme o tempo em `active_time_minutes`
3. Verifique se o MAC está correto no banco

## Estrutura da DATABASE_URL

```
mysql://usuario:senha@host:porta/banco
```

Exemplo:
```
mysql://root:password@localhost:3306/mikrotik_db
```

## Comandos no Console EasyPanel

```bash
# Ver logs em tempo real
tail -f /var/log/app.log

# Testar conexão manualmente
python -c "from disconnect_expired_users import get_db_connection; print(get_db_connection())"

# Executar verificação manual
RUN_ON_START=true python disconnect_expired_users.py
```