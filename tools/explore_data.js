// Exploração de dados financeiros - uso único
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
    if (Buffer.isBuffer(v)) o[k] = v.toString('latin1').substring(0, 80);
    else if (v instanceof Date) o[k] = v.toISOString().substring(0, 10);
    else o[k] = v;
  }
  return o;
}

Firebird.attach(options, async (err, db) => {
  if (err) { console.error('ERRO:', err.message); process.exit(1); }

  // 1. Range de datas
  const dr = await query(db, `SELECT MIN(DATACOMPETENCIA) as MIN_COMP, MAX(DATACOMPETENCIA) as MAX_COMP, MIN(DTPAGAMENTO) as MIN_PAG, MAX(DTPAGAMENTO) as MAX_PAG FROM VS_CONTASAPAGAR`);
  console.log('=== RANGE DATAS VS_CONTASAPAGAR ===', fmt(dr[0]));

  const dr2 = await query(db, `SELECT MIN(DATAEMISSAO) as MIN_EMI, MAX(DATAEMISSAO) as MAX_EMI, MIN(DATARECEBIMENTO) as MIN_REC, MAX(DATARECEBIMENTO) as MAX_REC FROM VS_CONTASARECEBER`);
  console.log('=== RANGE DATAS VS_CONTASARECEBER ===', fmt(dr2[0]));

  // 2. SITUACAO values
  const sit = await query(db, `SELECT SITUACAO, COUNT(*) as N FROM VS_CONTASAPAGAR GROUP BY SITUACAO ORDER BY SITUACAO`);
  console.log('\n=== SITUACOES (pagar) ==='); sit.forEach(r => console.log(' ', r.SITUACAO, '->', r.N));

  const sit2 = await query(db, `SELECT SITUACAO, COUNT(*) as N FROM VS_CONTASARECEBER GROUP BY SITUACAO ORDER BY SITUACAO`);
  console.log('\n=== SITUACOES (receber) ==='); sit2.forEach(r => console.log(' ', r.SITUACAO, '->', r.N));

  // 3. Titulos/Contas distintos de despesas (top 50)
  const titulos = await query(db, `SELECT FIRST 80 CODREDUZIDO, CONTA, TITULO, COUNT(*) as N FROM VS_CONTASAPAGAR GROUP BY CODREDUZIDO, CONTA, TITULO ORDER BY N DESC`);
  console.log('\n=== TOP TITULOS/CONTAS (despesas) ===');
  titulos.forEach(r => console.log(`  [${r.CODREDUZIDO}] ${r.CONTA} | ${r.TITULO ? r.TITULO.trim() : ''} (${r.N})`));

  // 4. Centros de custo
  const cc = await query(db, `SELECT CODCENTRO, NOME FROM CONCECUS01 WHERE SITUACAO='A   ' ORDER BY CODCENTRO`);
  console.log('\n=== CENTROS DE CUSTO ATIVOS ===');
  cc.forEach(r => console.log(`  [${r.CODCENTRO}] ${r.NOME.trim()}`));

  // 5. Plano de contas (receitas)
  const plcRec = await query(db, `SELECT CODREDUZIDO, CONTA, TITULO FROM FINVSPLC01 WHERE CONTA LIKE '4%' ORDER BY CONTA`);
  console.log('\n=== PLANO CONTAS RECEITAS (4.x) ===');
  plcRec.forEach(r => console.log(`  [${r.CODREDUZIDO}] ${r.CONTA} | ${r.TITULO ? r.TITULO.trim() : ''}`));

  // 6. Titulos/Contas de receitas
  const titRec = await query(db, `SELECT CODREDUZIDO, TITULO, COUNT(*) as N FROM VS_CONTASARECEBER GROUP BY CODREDUZIDO, TITULO ORDER BY N DESC`);
  console.log('\n=== TITULOS RECEITAS ===');
  // No column 'CONTA' in VS_CONTASARECEBER - check what's available
  titRec.slice(0, 30).forEach(r => console.log(`  [${r.CODREDUZIDO}] ${r.TITULO ? String(r.TITULO).trim() : 'null'} (${r.N})`));

  // 7. Produtos distintos em itens_venda
  const prods = await query(db, `SELECT FIRST 40 CONT_PRODUTO, DESCRICAO, COUNT(*) as N FROM VS_ITENS_VENDA GROUP BY CONT_PRODUTO, DESCRICAO ORDER BY N DESC`);
  console.log('\n=== PRODUTOS VENDIDOS (top 40) ===');
  prods.forEach(r => console.log(`  [${r.CONT_PRODUTO}] ${r.DESCRICAO ? r.DESCRICAO.trim() : ''} (${r.N} vendas)`));

  db.detach();
  console.log('\nConcluído.');
});
