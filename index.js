require('dotenv').config();
const cron = require('node-cron');
const { PrismaClient } = require('@prisma/client');
const RouterOsApi = require('node-routeros').default;

const prisma = new PrismaClient();

// Configurações do Mikrotik
const MIKROTIK_CONFIG = {
  host: process.env.MIKROTIK_HOST,
  username: process.env.MIKROTIK_USERNAME,
  password: process.env.MIKROTIK_PASSWORD,
  port: parseInt(process.env.MIKROTIK_PORT || '8728'),
};

// Tempo ativo padrão em minutos
const DEFAULT_ACTIVE_TIME_MINUTES = parseInt(process.env.DEFAULT_ACTIVE_TIME_MINUTES || '15');

// Função para obter o tempo ativo da configuração
async function getActiveTimeMinutes() {
  try {
    const confResults = await prisma.$queryRawUnsafe(`SELECT active_time_minutes FROM Conf LIMIT 1`);
    if (Array.isArray(confResults) && confResults.length > 0 && confResults[0].active_time_minutes > 0) {
      return confResults[0].active_time_minutes;
    }
  } catch (error) {
    console.error('Erro ao obter tempo ativo do banco de dados:', error);
  }
  return DEFAULT_ACTIVE_TIME_MINUTES;
}

// Função para conectar ao Mikrotik
async function connectToMikrotik() {
  const connection = new RouterOsApi({
    ...MIKROTIK_CONFIG,
    keepalive: true,
  });

  try {
    await connection.connect();
    console.log('✔ Conectado ao Mikrotik');
    return connection;
  } catch (error) {
    console.error('✖ Erro ao conectar ao Mikrotik:', error);
    throw error;
  }
}

// Função para remover entradas do Mikrotik
async function removeEntries(connection, path, field, mac) {
  try {
    console.log(`⟳ Verificando ${path} para MAC ${mac}`);
    
    const items = await connection.write(path + '/print', [`?${field}=${mac}`]);
    
    if (!items || items.length === 0) {
      console.log(`[${path}] nenhum registro para MAC ${mac}`);
      return;
    }
    
    for (const item of items) {
      const id = item['.id'];
      if (!id) {
        console.log(`[${path}] registro sem ID:`, item);
        continue;
      }
      
      try {
        await connection.write(path + '/remove', [`=.id=${id}`]);
        console.log(`[${path}] removido id=${id}`);
      } catch (error) {
        console.error(`[${path}] falha ao remover id=${id}:`, error);
      }
    }
  } catch (error) {
    console.error(`Erro ao processar ${path}:`, error);
  }
}

// Função para desconectar um usuário
async function disconnectUser(mac) {
  let connection;
  
  try {
    connection = await connectToMikrotik();
    
    // Remover cookies
    await removeEntries(connection, '/ip/hotspot/cookie', 'mac-address', mac);
    
    // Remover sessões ativas
    await removeEntries(connection, '/ip/hotspot/active', 'mac-address', mac);
    
    console.log(`✔ Usuário com MAC ${mac} desconectado`);
  } catch (error) {
    console.error(`Erro ao desconectar usuário com MAC ${mac}:`, error);
  } finally {
    if (connection) {
      connection.close();
    }
  }
}

// Função principal que verifica usuários expirados
async function checkExpiredUsers() {
  console.log('\n--- Iniciando verificação de usuários expirados ---');
  console.log(`Data/Hora: ${new Date().toLocaleString('pt-BR')}`);
  
  try {
    // Obter tempo ativo configurado
    const activeTimeMinutes = await getActiveTimeMinutes();
    console.log(`Tempo ativo configurado: ${activeTimeMinutes} minutos`);
    
    // Calcular o tempo limite
    const timeLimit = new Date();
    timeLimit.setMinutes(timeLimit.getMinutes() - activeTimeMinutes);
    console.log(`Verificando usuários com última atualização antes de: ${timeLimit.toLocaleString('pt-BR')}`);
    
    // Buscar usuários expirados
    const expiredUsers = await prisma.user.findMany({
      where: {
        updatedAt: {
          lt: timeLimit
        }
      },
      include: {
        login: true
      }
    });
    
    console.log(`Usuários expirados encontrados: ${expiredUsers.length}`);
    
    if (expiredUsers.length === 0) {
      console.log('Nenhum usuário expirado encontrado');
      return;
    }
    
    // Desconectar cada usuário expirado
    for (const user of expiredUsers) {
      console.log(`\nProcessando usuário: ${user.name} (MAC: ${user.mac})`);
      console.log(`Última atualização: ${user.updatedAt.toLocaleString('pt-BR')}`);
      
      // Desconectar o usuário do Mikrotik
      await disconnectUser(user.mac);
      
      // Atualizar o usuário como desconectado (opcional - você pode adicionar um campo 'disconnected' no modelo)
      // await prisma.user.update({
      //   where: { id: user.id },
      //   data: { disconnected: true }
      // });
    }
    
    console.log('\n✔ Verificação de usuários expirados concluída');
  } catch (error) {
    console.error('Erro durante a verificação de usuários:', error);
  }
}

// Função para iniciar o cron
function startCron() {
  const pattern = process.env.CRON_PATTERN || '*/5 * * * *';
  console.log(`Iniciando cron com padrão: ${pattern}`);
  
  // Agendar a tarefa
  cron.schedule(pattern, () => {
    checkExpiredUsers().catch(console.error);
  });
  
  console.log('Cron job iniciado com sucesso');
  console.log('Pressione Ctrl+C para parar');
  
  // Executar uma vez imediatamente para teste
  if (process.env.RUN_ON_START === 'true') {
    console.log('\nExecutando verificação inicial...');
    checkExpiredUsers().catch(console.error);
  }
}

// Manipular encerramento gracioso
process.on('SIGINT', async () => {
  console.log('\nEncerrando aplicação...');
  await prisma.$disconnect();
  process.exit(0);
});

// Iniciar a aplicação
async function main() {
  try {
    // Testar conexão com o banco
    await prisma.$connect();
    console.log('✔ Conectado ao banco de dados');
    
    // Iniciar o cron
    startCron();
  } catch (error) {
    console.error('Erro ao iniciar aplicação:', error);
    await prisma.$disconnect();
    process.exit(1);
  }
}

// Executar
main();