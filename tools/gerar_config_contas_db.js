/**
 * Gera sugestões de mapeamento para config_contas.csv baseado nas contas do banco.
 * Compara os TITULOS do banco com o config atual e lista os que estão faltando.
 *
 * Uso: node tools/gerar_config_contas_db.js
 */
const Firebird = require('node-firebird');
const fs = require('fs');
const path = require('path');

const options = {
  host: '192.168.100.201', port: 3050,
  database: '/opt/Auditor/Dados/AUDITOR.FDB',
  user: 'RO_AUDITOR', password: '3@mores',
  lowercase_keys: false, charSet: 'WIN1252',
};

function query(db, sql) {
  return new Promise((res, rej) => db.query(sql, [], (e, r) => e ? rej(e) : res(r)));
}

// Lê config_contas.csv atual
const configPath = path.join(__dirname, '..', 'config', 'config_contas.csv');
const configLinhas = fs.readFileSync(configPath, 'utf8').split('\n');
const contasMapeadas = new Set(
  configLinhas.slice(1).map(l => l.split(';')[0].trim().toUpperCase()).filter(Boolean)
);
console.log(`Config atual: ${contasMapeadas.size} contas mapeadas\n`);

Firebird.attach(options, async (err, db) => {
  if (err) { console.error('ERRO:', err.message); process.exit(1); }

  // Títulos usados no banco com contagem
  const titulos = await query(db, `
    SELECT TITULO, COUNT(*) as N, SUM(VALOR_FINAL) as TOTAL
    FROM VS_CONTASAPAGAR
    WHERE TITULO IS NOT NULL AND TITULO <> '' AND SITUACAO <> 3
    GROUP BY TITULO
    ORDER BY N DESC
  `);

  console.log('=== CONTAS JÁ MAPEADAS (no banco E no config) ===');
  const mapeadas = titulos.filter(r => contasMapeadas.has((r.TITULO||'').trim().toUpperCase()));
  console.log(`  ${mapeadas.length} contas\n`);

  console.log('=== CONTAS FALTANDO NO CONFIG (estão no banco mas não no config_contas.csv) ===');
  console.log('  Formato: nome_conta;SUGESTAO_LINHA_DRE;DESPESA_DIRETA;\n');

  const faltando = titulos.filter(r => {
    const t = (r.TITULO||'').trim().toUpperCase();
    return t && !contasMapeadas.has(t);
  });

  // Sugere linha_dre baseada em palavras-chave
  function sugerir(titulo) {
    const t = titulo.toUpperCase();
    if (t.includes('SALÁRIO') || t.includes('SALARIO') || t.includes('REMUNERAÇÃO') || t.includes('PRÓ-LABORE') || t.includes('PRO-LABORE')) return 'OPER_FOLHA';
    if (t.includes('FGTS') || t.includes('INSS') || t.includes('ENCARGO') || t.includes('RESCISÃO') || t.includes('FÉRIAS') || t.includes('FERIAS') || t.includes('13') || t.includes('PLR') || t.includes('GRRF')) return 'OPER_ENCARGOS';
    if (t.includes('ENERGIA') || t.includes('LUZ')) return 'CMV_ENERGIA';
    if (t.includes('DIESEL') || t.includes('GASOLINA') || t.includes('COMBUSTÍVEL') || t.includes('COMBUSTIVEL')) return 'OPER_DIESEL';
    if (t.includes('RAÇÃO') || t.includes('RACAO') || t.includes('NUCLEO') || t.includes('FARELO') || t.includes('MILHO') || t.includes('SOJA')) return 'CMV_NUCLEO';
    if (t.includes('EMBALAGEM') || t.includes('CAIXA') || t.includes('BANDEJA')) return 'CMV_EMBAL';
    if (t.includes('MEDICAMENTO') || t.includes('VETERINÁR') || t.includes('VACINA') || t.includes('SAÚDE')) return 'CMV_SAUDE';
    if (t.includes('EPI') || t.includes('EPC') || t.includes('PROTEÇÃO')) return 'CMV_EPI';
    if (t.includes('MANUTENÇÃO') || t.includes('MANUTENCAO') || t.includes('REPARO') || t.includes('BORRACHARIA')) return 'CMV_MANUT';
    if (t.includes('FRETE') || t.includes('TRANSPORTE') || t.includes('CARRETO')) return 'OPER_FRETE';
    if (t.includes('ALUGUEL') || t.includes('LOCAÇÃO') || t.includes('LOCACAO')) return 'OPER_ALUGUEL';
    if (t.includes('IMPOSTO') || t.includes('IRPJ') || t.includes('CSLL') || t.includes('ICMS') || t.includes('PIS') || t.includes('COFINS')) return 'IMP_IRPJ';
    if (t.includes('EMPRÉSTIMO') || t.includes('EMPRESTIMO') || t.includes('FINANCIAMENTO') || t.includes('PARCELA')) return 'OPER_OUTRASFIX';
    if (t.includes('ADIANTAMENTO')) return 'IGNORAR';
    if (t.includes('TRANSFERÊNCIA') || t.includes('TRANSFERENCIA')) return 'IGNORAR';
    if (t.includes('CAPEX') || t.includes('IMOBILIZADO') || t.includes('BENFEITORIA') || t.includes('OBRA')) return 'CAPEX_REFBENF';
    if (t.includes('CONTADOR') || t.includes('CONTABILIDADE')) return 'OPER_CONTADOR';
    if (t.includes('INTERNET') || t.includes('TELEFONE')) return 'OPER_INTERNET';
    if (t.includes('REFEIÇÃO') || t.includes('REFEICAO') || t.includes('ALIMENTAÇÃO')) return 'OPER_REFEI';
    return '???';
  }

  let csvSugestoes = '# Sugestões geradas automaticamente — revisar antes de usar\n';
  csvSugestoes += '# nome_conta;linha_dre;natureza;tipo_estoque\n';

  faltando.forEach(r => {
    const t = (r.TITULO||'').trim();
    const total = (r.TOTAL||0)/100; // valores podem estar em centavos
    const sug = sugerir(t);
    const nat = sug.startsWith('CMV_') ? 'DESPESA_DIRETA' : sug.startsWith('CAPEX_') ? 'CAPEX' : sug === 'IGNORAR' ? 'IGNORAR' : 'DESPESA_DIRETA';
    console.log(`  ${String(r.N).padStart(4)}x  R$ ${String(Math.round(total)).padStart(10)}  ${t}`);
    console.log(`         → sugestão: ${sug}`);
    csvSugestoes += `${t};${sug};${nat};\n`;
  });

  // Salva arquivo de sugestões
  const outPath = path.join(__dirname, '..', 'config', 'config_contas_sugestoes.csv');
  fs.writeFileSync(outPath, csvSugestoes, 'utf8');
  console.log(`\n${faltando.length} contas faltando → sugestões salvas em config/config_contas_sugestoes.csv`);

  // Contas com null TITULO
  const semConta = await query(db, `
    SELECT IDPAGAMENTO, COUNT(*) as N FROM VS_CONTASAPAGAR
    WHERE (TITULO IS NULL OR TITULO = '') AND SITUACAO <> 3
    GROUP BY IDPAGAMENTO ORDER BY N DESC
  `);
  console.log(`\n=== LANÇAMENTOS SEM TITULO (${semConta.reduce((s,r)=>s+r.N,0)} total) ===`);
  semConta.slice(0, 20).forEach(r => console.log(`  ${String(r.N).padStart(4)}x  TIPO: ${r.IDPAGAMENTO||'null'}`));

  db.detach();
});
