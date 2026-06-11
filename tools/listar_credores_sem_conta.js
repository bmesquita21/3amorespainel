// Lista fornecedores com NFs sem conta contábil (para config_fornecedores.csv)
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

Firebird.attach(options, async (err, db) => {
  if (err) { console.error('ERRO:', err.message); process.exit(1); }

  const rows = await query(db, `
    SELECT CREDOR, CENTROCUSTO,
           COUNT(*) as N,
           SUM(VALOR_FINAL) as TOTAL
    FROM VS_CONTASAPAGAR
    WHERE (TITULO IS NULL OR TITULO = '')
      AND SITUACAO <> 3
    GROUP BY CREDOR, CENTROCUSTO
    ORDER BY N DESC
  `);

  console.log('credor;centrocusto;ocorrencias;total;linha_dre_sugerida;natureza');
  rows.forEach(r => {
    const t = (r.CREDOR||'').toUpperCase();
    let sug = '???';
    if (/AGROCERES|NUTRICAO|RACAO|NUTRECO|NUVITAL|PREMIX|NOVINTEC|HENDRIX|BOEHRINGER/.test(t)) sug = 'CMV_NUCLEO';
    else if (/GRANJA|POEDEIRA|PINTAINHA|PINTA/.test(t)) sug = 'CMV_OUTROS';
    else if (/GISALTO|AUTO PEÇA|AUTOPECA|PNEU|BORRACHA/.test(t)) sug = 'CMV_MANUT';
    else if (/ENERGIA|LIGHT|ENEL|COPEL|CEMIG|COELBA|CEEL|CEMAR/.test(t)) sug = 'CMV_ENERGIA';
    else if (/GRAFICA|EMBALAGEM|CAIXA|BANDEJA|CARTUCHO/.test(t)) sug = 'CMV_EMBAL';
    else if (/FARMÁCIA|FARMACIA|VETERINÁR|VETERINAR|VACINA|MEDICAMENTO/.test(t)) sug = 'CMV_SAUDE';
    else if (/COMBUSTÍVEL|COMBUSTIVEL|PETROBRAS|POSTO|IPIRANGA|SHELL/.test(t)) sug = 'OPER_DIESEL';
    else if (/BRADESCO|SANTANDER|ITAÚ|ITAU|BB |BANCO DO BRASIL|SICOOB|SAFRA/.test(t)) sug = 'IGNORAR';
    const nat = sug === 'IGNORAR' ? 'IGNORAR' : sug.startsWith('CMV_') ? 'DESPESA_DIRETA' : 'DESPESA_DIRETA';
    console.log(`${(r.CREDOR||'').trim()};${(r.CENTROCUSTO||'').trim()};${r.N};${Math.round(r.TOTAL||0)};${sug};${nat}`);
  });

  db.detach();
});
