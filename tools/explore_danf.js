// Investigar como obter conta contábil dos lançamentos DANF (NF compra)
const Firebird = require('node-firebird');

const options = {
  host: '192.168.100.201', port: 3050,
  database: '/opt/Auditor/Dados/AUDITOR.FDB',
  user: 'RO_AUDITOR', password: '3@mores',
  lowercase_keys: false, charSet: 'WIN1252',
};

function query(db, sql) {
  return new Promise((res, rej) => db.query(sql, [], (e, r) => e ? rej(e) : res(r)));
}
function fmt(row) {
  const o = {};
  for (const [k, v] of Object.entries(row)) {
    if (Buffer.isBuffer(v)) o[k] = v.toString('latin1').substring(0, 80).trim();
    else if (v instanceof Date) o[k] = v.toISOString().substring(0, 10);
    else if (typeof v === 'number' && !Number.isInteger(v)) o[k] = Math.round(v * 100) / 100;
    else o[k] = v;
  }
  return o;
}

Firebird.attach(options, async (err, db) => {
  if (err) { console.error('ERRO:', err.message); process.exit(1); }

  // 1. Ver colunas completas de VS_CONTASAPAGAR para entradas DANF
  const danfCols = await query(db, `SELECT FIRST 3 * FROM VS_CONTASAPAGAR WHERE IDPAGAMENTO = 'DANF - DANF'`);
  console.log('=== AMOSTRA DANF (todas colunas) ===');
  danfCols.forEach(r => console.log(JSON.stringify(fmt(r))));

  // 2. Ver CMPNFR01001 colunas — NF de compra
  const nfrCols = await query(db, `
    SELECT f.RDB$FIELD_NAME FROM RDB$RELATION_FIELDS f
    WHERE f.RDB$RELATION_NAME = 'CMPNFR01001' ORDER BY f.RDB$FIELD_POSITION
  `);
  console.log('\n=== CMPNFR01001 colunas ===');
  console.log(nfrCols.map(c => c.RDB$FIELD_NAME.trim()).join(', '));

  // 3. Tentar join entre VS_CONTASAPAGAR e CMPNFR01001 via CONT_NOTA (ou similar)
  try {
    const join1 = await query(db, `
      SELECT FIRST 3
        p.CONTROLE, p.CREDOR, p.VALOR_FINAL, p.CENTROCUSTO,
        n.CONT_NOTA, n.NATUREZAOPERACAO, n.NOTAFISCAL
      FROM VS_CONTASAPAGAR p
      JOIN CMPNFR01001 n ON n.CONT_NOTA = p.CONTROLE
      WHERE p.IDPAGAMENTO = 'DANF - DANF'
    `);
    console.log('\n=== JOIN via CONTROLE=CONT_NOTA ===');
    join1.forEach(r => console.log(JSON.stringify(fmt(r))));
  } catch(e) { console.log('Join CONTROLE=CONT_NOTA falhou:', e.message); }

  // 4. Tentar via CMPITMPE (itens de pedido de compra)
  // Verificar colunas de CMPPEDID01001
  const pedCols = await query(db, `
    SELECT f.RDB$FIELD_NAME FROM RDB$RELATION_FIELDS f
    WHERE f.RDB$RELATION_NAME = 'CMPPEDID01001' ORDER BY f.RDB$FIELD_POSITION
  `);
  console.log('\n=== CMPPEDID01001 colunas ===');
  console.log(pedCols.map(c => c.RDB$FIELD_NAME.trim()).join(', '));

  // 5. Ver FINPAGAM01001 (tabela base de contas a pagar)
  const finCols = await query(db, `
    SELECT f.RDB$FIELD_NAME FROM RDB$RELATION_FIELDS f
    WHERE f.RDB$RELATION_NAME = 'FINPAGAM01001' ORDER BY f.RDB$FIELD_POSITION
  `);
  console.log('\n=== FINPAGAM01001 colunas ===');
  console.log(finCols.map(c => c.RDB$FIELD_NAME.trim()).join(', '));

  // 6. Amostra de FINPAGAM01001 para DANF
  try {
    const fpam = await query(db, `SELECT FIRST 2 * FROM FINPAGAM01001 WHERE TIPODOC = 'DANF' OR IDPAGAMENTO = 'DANF'`);
    console.log('\n=== FINPAGAM01001 amostra DANF ===');
    fpam.forEach(r => console.log(JSON.stringify(fmt(r))));
  } catch(e) { console.log('Amostra FINPAGAM01001 falhou:', e.message); }

  // 7. Ver CMPNFR com join para conta
  try {
    const nfrAcnt = await query(db, `
      SELECT FIRST 5
        n.CONT_NOTA, n.NOTAFISCAL, n.DATAENTRADA,
        f.CODREDUZIDO, plc.TITULO,
        n.NATUREZAOPERACAO
      FROM CMPNFR01001 n
      LEFT JOIN FINPAGAM01001 f ON f.CONT_NOTA = n.CONT_NOTA
      LEFT JOIN FINVSPLC01 plc ON plc.CODREDUZIDO = f.CODREDUZIDO
      WHERE n.DATAENTRADA IS NOT NULL
      ORDER BY n.DATAENTRADA DESC
    `);
    console.log('\n=== CMPNFR01001 JOIN FINPAGAM01001 JOIN FINVSPLC01 ===');
    nfrAcnt.forEach(r => console.log(JSON.stringify(fmt(r))));
  } catch(e) { console.log('Join NF+FIN+PLC falhou:', e.message); }

  // 8. Verificar VS_CONTASAPAGAR — qual campo liga à NF
  const cpagar = await query(db, `SELECT FIRST 1 * FROM VS_CONTASAPAGAR WHERE IDPAGAMENTO = 'DANF - DANF'`);
  if (cpagar.length) {
    console.log('\n=== VS_CONTASAPAGAR DANF — TODAS COLUNAS ===');
    const row = cpagar[0];
    Object.entries(row).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '' && v !== 0)
        console.log(`  ${k}: ${Buffer.isBuffer(v) ? v.toString('latin1').trim() : (v instanceof Date ? v.toISOString().substring(0,10) : v)}`);
    });
  }

  db.detach();
  console.log('\nConcluído.');
});
