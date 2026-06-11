// Exploração do schema Firebird - uso único, não commitar
const Firebird = require('node-firebird');

const options = {
  host: '192.168.100.201',
  port: 3050,
  database: '/opt/Auditor/Dados/AUDITOR.FDB',
  user: 'RO_AUDITOR',
  password: '3@mores',
  lowercase_keys: false,
  role: null,
  pageSize: 4096,
  charSet: 'WIN1252',
};

function query(db, sql) {
  return new Promise((resolve, reject) => {
    db.query(sql, [], (err, result) => {
      if (err) reject(err);
      else resolve(result);
    });
  });
}

Firebird.attach(options, async (err, db) => {
  if (err) { console.error('CONEXAO FALHOU:', err.message); process.exit(1); }
  console.log('Conectado com sucesso!\n');

  try {
    // Lista todas as tabelas de usuário
    const tables = await query(db, `
      SELECT RDB$RELATION_NAME
      FROM RDB$RELATIONS
      WHERE RDB$SYSTEM_FLAG = 0
        AND RDB$VIEW_BLR IS NULL
      ORDER BY RDB$RELATION_NAME
    `);
    console.log('=== TABELAS ===');
    tables.forEach(t => console.log(' ', t.RDB$RELATION_NAME.trim()));

    // Lista views
    const views = await query(db, `
      SELECT RDB$RELATION_NAME
      FROM RDB$RELATIONS
      WHERE RDB$SYSTEM_FLAG = 0
        AND RDB$VIEW_BLR IS NOT NULL
      ORDER BY RDB$RELATION_NAME
    `);
    console.log('\n=== VIEWS ===');
    views.forEach(v => console.log(' ', v.RDB$RELATION_NAME.trim()));

    // Para tabelas com nomes financeiros, mostra colunas
    const interesting = tables
      .map(t => t.RDB$RELATION_NAME.trim())
      .filter(n => /LANC|CONTA|CENTRO|RECEI|DESPE|PAGAM|RECEB|CAIXA|FLUXO|PRODU|ESTOQUE|CLIENTE|FORNEC|PEDIDO|NOTA|NF|SALDO|EXTRATO|MOVIMENTO/i.test(n));

    console.log('\n=== TABELAS FINANCEIRAS ENCONTRADAS ===');
    for (const tbl of interesting) {
      const cols = await query(db, `
        SELECT f.RDB$FIELD_NAME, t.RDB$TYPE_NAME
        FROM RDB$RELATION_FIELDS f
        LEFT JOIN RDB$TYPES t ON t.RDB$FIELD_NAME = 'RDB$FIELD_TYPE'
          AND t.RDB$TYPE = (
            SELECT ff.RDB$FIELD_TYPE FROM RDB$FIELDS ff
            WHERE ff.RDB$FIELD_NAME = f.RDB$FIELD_SOURCE
          )
        WHERE f.RDB$RELATION_NAME = '${tbl}'
        ORDER BY f.RDB$FIELD_POSITION
      `);
      const count = await query(db, `SELECT COUNT(*) as N FROM "${tbl}"`);
      console.log(`\n[${tbl}] (${count[0].N} registros)`);
      cols.forEach(c => console.log(`  - ${c.RDB$FIELD_NAME.trim()} (${c.RDB$TYPE_NAME ? c.RDB$TYPE_NAME.trim() : '?'})`));

      // Amostra de 2 linhas
      try {
        const sample = await query(db, `SELECT FIRST 2 * FROM "${tbl}"`);
        if (sample.length) {
          console.log('  Amostra:', JSON.stringify(sample[0]).substring(0, 200));
        }
      } catch(e) { /* ignora */ }
    }

  } catch(e) {
    console.error('Erro:', e.message);
  }

  db.detach();
});
