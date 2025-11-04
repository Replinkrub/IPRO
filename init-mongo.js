// Script de inicialização do MongoDB para o IPRO
db = db.getSiblingDB('ipro');

// Criar usuário para a aplicação
db.createUser({
  user: 'ipro_user',
  pwd: 'ipro_pass',
  roles: [
    {
      role: 'readWrite',
      db: 'ipro'
    }
  ]
});

// Criar coleções com validação
db.createCollection('datasets', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'status', 'created_at', 'hash'],
      properties: {
        name: { bsonType: 'string' },
        status: { 
          bsonType: 'string',
          enum: ['PROCESSING', 'READY', 'FAILED']
        },
        created_at: { bsonType: 'date' },
        hash: { bsonType: 'string' },
        files: { bsonType: 'array' },
        stats: { bsonType: 'object' }
      }
    }
  }
});

db.createCollection('transactions');
db.createCollection('customers');
db.createCollection('analytics_customer');
db.createCollection('analytics_product');
db.createCollection('requests');

print('Banco de dados IPRO inicializado com sucesso!');

