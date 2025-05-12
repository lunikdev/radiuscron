require('dotenv').config();
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
    console.log('Tentando conectar ao Mikrotik...');
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
  }
}

// Executar teste
testConnection();