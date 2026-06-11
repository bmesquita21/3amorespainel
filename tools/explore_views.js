// Exploração das views financeiras - uso único
const Firebird = require('node-firebird');

const options = {
  host: '192.168.100.201',
  port: 3050,
  database: '/opt/Auditor/Dados/AUDITOR.FDB',
  user: 'RO_AUDITOR',
  password: '3@mores',
  lowercase_keys: false,
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

function fmtRow(row) {
  const out = {};
  for (const [k, v] of Object.entries(row)) {
    if (Buffer.isBuffer(v)) out[k] = v.toString('latin1').substring(0, 50);
    else if (v instanceof Date) out[k] = v.toISOString().substring(0, 10);
    else out[k] = v;
  }
  return out;
}

const VIEWS = [
  'AMORES_CUSTOOVO',
  'AMORES_FINANCEIRO_INTEGRADO',
  'VS_CONTASAPAGAR',
  'VS_CONTASARECEBER',
  'VS_ENTRADASAIDA',
  'VS_VENDAS',
  'VS_ITENS_VENDA',
  'VS_PEDIDO',
  'FINVSIPG',
  'FINVSPLC01',
  'FINVSBDA01',
  'CONLANCA01',
  'CONCECUS01',
  'CONCONTB01',
  'CONHISTO01',
  'CONSALDO01',
];

Firebird.attach(options, async (err, db) => {
  if (err) { console.error('CONEXAO FALHOU:', err.message); process.exit(1); }

  for (const view of VIEWS) {
    try {
      // Colunas
      const cols = await query(db, `
        SELECT f.RDB$FIELD_NAME
        FROM RDB$RELATION_FIELDS f
        WHERE f.RDB$RELATION_NAME = '${view}'
        ORDER BY f.RDB$FIELD_POSITION
      `);
      // Contagem
      const cnt = await query(db, `SELECT COUNT(*) as N FROM "${view}"`);
      console.log(`\n=== ${view} (${cnt[0].N} registros) ===`);
      console.log('Colunas:', cols.map(c => c.RDB$FIELD_NAME.trim()).join(', '));

      // Amostra
      const rows = await query(db, `SELECT FIRST 3 * FROM "${view}"`);
      rows.forEach((r, i) => {
        console.log(`  [${i}]`, JSON.stringify(fmtRow(r)).substring(0, 400));
      });
    } catch(e) {
      console.log(`\n=== ${view} === ERRO: ${e.message}`);
    }
  }

  db.detach();
  console.log('\nConcluído.');
});
