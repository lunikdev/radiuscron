// Removido require('dotenv').config();
const RouterOsApi = require('node-routeros').default;

// Testar conexão com o Mikrotik
async function testConnection() {
  const connection = new RouterOsApi({
    host: process.env.MIKROTIK_HOST,
    username: process.env.MIKROTIK_USERNAME,
    password: process.env.MIKROTIK_PASSWORD,
    port: parseInt(process.env.MIKROTIK_PORT || '8728'),
  });

  try {
    console.log('Configurações:');
    console.log(`- Host: ${process.env.MIKROTIK_HOST}`);
    console.log(`- Username: ${process.env.MIKROTIK_USERNAME}`);
    console.log(`- Port: ${process.env.MIKROTIK_PORT || '8728'}`);
    console.log('\nTentando conectar ao Mikrotik...');
    
    await connection.connect();
    console.log('✔ Conectado com sucesso!');
    
    // Obter informações do sistema
    const systemInfo = await connection.write('/system/identity/print');
    console.log('Sistema:', systemInfo);
    
    // Listar sessões ativas
    const activeSessions = await connection.write('/ip/hotspot/active/print');
    console.log(`\nSessões ativas: ${activeSessions.length}`);
    
    if (activeSessions.length > 0) {
      console.log('\nPrimeiras 5 sessões:');
      activeSessions.slice(0, 5).forEach((session, index) => {
        console.log(`${index + 1}. MAC: ${session['mac-address']}, User: ${session.user}, IP: ${session.address}`);
      });
    }
    
    connection.close();
    console.log('\n✔ Conexão fechada');
  } catch (error) {
    console.error('✖ Erro ao conectar:', error);
    
    if (error.message.includes('ECONNREFUSED')) {
      console.error('\nPossíveis causas:');
      console.error('1. O IP do Mikrotik está incorreto');
      console.error('2. A API do Mikrotik não está habilitada');
      console.error('3. A porta da API está incorreta');
      console.error('4. Firewall bloqueando a conexão');
    } else if (error.message.includes('Authentication')) {
      console.error('\nPossíveis causas:');
      console.error('1. Usuário ou senha incorretos');
      console.error('2. O usuário não tem permissões de API');
    }
  }
}

// Verificar variáveis de ambiente
const requiredVars = ['MIKROTIK_HOST', 'MIKROTIK_USERNAME', 'MIKROTIK_PASSWORD'];
const missingVars = requiredVars.filter(varName => !process.env[varName]);

if (missingVars.length > 0) {
  console.error(`Erro: Variáveis de ambiente obrigatórias não definidas: ${missingVars.join(', ')}`);
  process.exit(1);
}

// Executar teste
testConnection();
