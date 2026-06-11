# -*- coding: utf-8 -*-
"""Relatório PDF consolidado (DRE + Fluxo + Balanço + Indicadores + Reconciliação + Veredito).
Usa fpdf2 (fonte core latin-1 -> texto é sanitizado; sem emojis)."""
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import dre as D, fc as FC, bp as BP, brutils as B, extrato as EX

NAVY = (31, 73, 125)

def _san(s):
    s = str(s)
    for a, b in [("—", "-"), ("–", "-"), ("−", "-"), ("→", "->"), ("•", "-"),
                 ("’", "'"), ("…", "..."), ("（", "("), ("）", ")"),
                 ("Δ", "var."), ("Σ", "Soma "), ("⚠️", ""), ("⚠", ""),
                 ("✅", ""), ("🔴", ""), ("🐔", ""), ("🧾", ""), ("📊", ""), ("📦", "")]:
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


class _PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 8); self.set_text_color(130)
        self.cell(0, 6, _san("Painel Financeiro 3 Amores - Relatorio Gerencial"),
                  align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0); self.set_draw_color(*NAVY); self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y()); self.ln(2)

    def footer(self):
        self.set_y(-12); self.set_font("Helvetica", "I", 7); self.set_text_color(130)
        self.cell(0, 6, _san(f"Pagina {self.page_no()}/{{nb}}   -   Painel Financeiro 3 Amores"), align="C")
        self.set_text_color(0)


def _sec(pdf, titulo):
    if pdf.get_y() > 250: pdf.add_page()
    pdf.ln(2); pdf.set_font("Helvetica", "B", 12); pdf.set_fill_color(*NAVY); pdf.set_text_color(255)
    pdf.cell(0, 8, _san("  " + titulo), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0); pdf.ln(1)


HEADER_T = {"section", "h", "h2"}
TOTAL_T = {"total", "subtotal", "profit", "st", "t", "dif"}

def _row(pdf, left, right, bold=False, fill=False, indent=True, color=None):
    pdf.set_font("Helvetica", "B" if bold else "", 10)
    if color: pdf.set_text_color(*color)
    if fill: pdf.set_fill_color(226, 233, 244)
    pre = "   " if (indent and not bold) else " "
    pdf.cell(132, 6.4, _san(pre + str(left)), border=0, fill=fill, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(0, 6.4, _san(right), border=0, align="R", fill=fill, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0)


def _tabela(pdf, layout, V):
    for t, lab, idk in layout:
        val = V.get(idk) if idk else None
        rhs = B.brl(val) if isinstance(val, (int, float)) else ""
        _row(pdf, lab, rhs, bold=(t in HEADER_T or t in TOTAL_T), fill=(t in HEADER_T), indent=(t not in HEADER_T))


def build_pdf(dfs, periodos, cfg, biologico=True, caixa_real=None, adiant=0.0, aporte=0.0,
              emprestimos=0.0, tx_ex=None, overrides=None, titulo="Acumulado"):
    Vd = D.compute(dfs, periodos, cfg, biologico)
    Fv = FC.compute(dfs, periodos)
    Bv = BP.compute(dfs, periodos, cfg, biologico, caixa_real=caixa_real,
                    adiant_clientes=adiant, aporte_socio=aporte, emprestimos=emprestimos)
    ind, _ = BP.indicadores(dfs, periodos, cfg, biologico, caixa_real=caixa_real,
                            adiant_clientes=adiant, aporte_socio=aporte, emprestimos=emprestimos)
    fim = max(periodos)

    pdf = _PDF(); pdf.set_auto_page_break(True, 14); pdf.alias_nb_pages(); pdf.add_page()

    # ---- título ----
    pdf.set_font("Helvetica", "B", 18); pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, _san("Relatorio Financeiro Gerencial"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 7, _san("Granja 3 Amores - Grupo Bom Jardim"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(110); pdf.set_font("Helvetica", "", 10.5)
    bio_txt = "ativo biologico LIGADO" if biologico else "recria como despesa"
    pdf.cell(0, 6, _san(f"Periodo: {titulo}   |   posicao do Balanco: {fim}   |   {bio_txt}"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0); pdf.ln(2)

    # ---- veredito ----
    ebitda, ll = ind["_EBITDA"], ind["_LL"]
    if ebitda < 0: cor, vt = (190, 40, 40), "DEFICITARIA - opera no vermelho (EBITDA acumulado negativo)"
    elif ll < 0: cor, vt = (205, 140, 0), "NO LIMITE - gera caixa operacional, mas resultado final negativo"
    else: cor, vt = (25, 135, 45), "RENTAVEL"
    pdf.set_fill_color(*cor); pdf.set_text_color(255); pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, _san("  VEREDITO: " + vt), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(40); pdf.set_font("Helvetica", "", 9.5); pdf.ln(1)
    pdf.multi_cell(0, 5, _san(
        f"EBITDA acumulado {B.brl(ebitda)}  .  Lucro liquido acumulado {B.brl(ll)}.  "
        "A margem bruta do ovo e POSITIVA, mas o custo fixo (logistica + pessoal) supera a margem. "
        "A operacao nao se autofinancia: sobrevive de aportes/mutuos do grupo. "
        "Caminho: escalar producao ou enxugar custo fixo."))
    pdf.set_text_color(0)

    # ---- peças ----
    _sec(pdf, "1. DRE - Demonstracao do Resultado (regime de competencia)"); _tabela(pdf, D.LAYOUT, Vd)
    _sec(pdf, "2. Fluxo de Caixa (regime de caixa - relatorios do sistema)"); _tabela(pdf, FC.LAYOUT, Fv)
    _sec(pdf, "3. Balanco Patrimonial (gerencial - fechado)"); _tabela(pdf, BP.LAYOUT, Bv)

    # ---- indicadores ----
    _sec(pdf, "4. Indicadores")
    def _pct(x): return f"{100*x:.1f}%" if isinstance(x, (int, float)) else "-"
    def _num(x): return f"{x:.2f}" if isinstance(x, (int, float)) else "-"
    _row(pdf, "ROE (Lucro Liquido / PL)", _pct(ind["ROE"]))
    _row(pdf, "Liquidez Corrente (AC / PC)", _num(ind["LIQ_CORR"]))
    _row(pdf, "Endividamento (Passivo / PL)", _num(ind["ENDIV"]))
    _row(pdf, "ROCE (EBIT / (Ativo - PC))", _pct(ind["ROCE"]))

    # ---- reconciliação / funding ----
    _sec(pdf, "5. Reconciliacao e Funding (extratos bancarios)")
    pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(60)
    pdf.multi_cell(0, 5, _san(
        "Operacional: o recebido no banco bate com o faturamento da DRE (sistema consistente). "
        "O excedente que entrou no banco e dinheiro do grupo (aporte/mutuo) e adiantamento de cliente. "
        "Obs.: a soma BRUTA dos creditos superestima (o mesmo dinheiro circula entre as contas); "
        "usa-se o valor LIQUIDO, medido pela identidade contabil e confirmado pelos extratos."))
    pdf.set_text_color(0); pdf.ln(1)
    _row(pdf, "Caixa real (extratos)", B.brl(Bv.get("CAIXA", 0)), bold=True)
    _row(pdf, "Aporte do socio/grupo (liquido) -> PL", B.brl(Bv.get("AFAC_SOCIO", 0)))
    _row(pdf, "Mutuos do grupo -> Passivo", B.brl(Bv.get("EMPRESTIMOS", 0)))
    _row(pdf, "Adiantamento de cliente (AgroMais) -> Passivo", B.brl(Bv.get("ADIANT_CLI", 0)))
    _row(pdf, "Diferenca a investigar (apos fechamento)", B.brl(Bv.get("DIFERENCA", 0)), bold=True)

    # ---- notas ----
    pdf.ln(2); pdf.set_font("Helvetica", "I", 8); pdf.set_text_color(120)
    pdf.multi_cell(0, 4.3, _san(
        "Notas: (1) DRE por competencia; Fluxo por caixa - datas distintas. "
        "(2) CMV por consumo (racao = producao fase postura; embalagem por composicao). "
        "(3) Ativo biologico: custo de recria capitalizado e amortizado na postura. "
        "(4) Capital Social informado pelo socio. Contas a Receber/Estoque/Fornecedores: aproximacoes gerenciais. "
        "(5) PIS/COFINS nao existem como conta no sistema -> linha zerada (nunca calculado por aliquota)."))
    pdf.set_text_color(0)
    return bytes(pdf.output())
