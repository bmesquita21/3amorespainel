# -*- coding: utf-8 -*-
"""Valida o parser de TRANSACOES: abertura + Sfluxo == fechamento detectado (saldo corrido)
e == abertura do mes seguinte (cadeia). So entao confiamos na reconciliacao."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import extrato as E

def brl(v):
    if v is None: return "       —      "
    return f"{v:>15,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tx, rs = E.load_transacoes(ROOT)
print(f"transacoes: {len(tx)} | conta-meses: {len(rs)}\n")

# cadeia: abertura do mes seguinte por conta
rs = rs.sort_values(["chave", "ano", "mes"]).reset_index(drop=True)
rs["ord"] = rs.ano * 12 + rs.mes
rs["abertura_prox"] = rs.groupby("chave")["abertura"].shift(-1)

print("=" * 120)
print("VALIDACAO POR CONTA-MES")
print(f"{'periodo':8s} {'conta':26s} {'abertura':>15s} {'entradas':>15s} {'saidas':>15s} {'=fech_calc':>15s} {'fech_detec':>15s}  check")
print("=" * 120)
tot_ok = tot_bad = 0
for _, r in rs.iterrows():
    calc = (r.abertura or 0) + r.fluxo
    chk = ""
    # 1) fluxo bate com saldo corrido detectado?
    if r.fech_detectado is not None and r.abertura is not None:
        d = abs(calc - r.fech_detectado)
        if d < 1.0: chk = "OK-corrido"; tot_ok += 1
        else: chk = f"DIF {brl(calc - r.fech_detectado)}"; tot_bad += 1
    # 2) senao, cadeia: fech_calc bate com abertura do proximo mes? (Bradesco)
    elif r.abertura_prox is not None and r.abertura is not None:
        d = abs(calc - r.abertura_prox)
        if d < 1.0: chk = "OK-cadeia"; tot_ok += 1
        else: chk = f"DIF-cad {brl(calc - r.abertura_prox)}"; tot_bad += 1
    else:
        chk = "s/ ref"
    print(f"{r.periodo:8s} {(r.banco+'/'+r.titular):26s} {brl(r.abertura)} {brl(r.entradas)} {brl(r.saidas)} {brl(calc)} {brl(r.fech_detectado)}  {chk}")

print("=" * 120)
print(f"OK={tot_ok}  problemas={tot_bad}")

# checagem extra Bradesco: fech_detectado == abertura do proximo mes (cadeia independente)
print("\nCADEIA BRADESCO (fech_detectado[M] deve == abertura[M+1]):")
brad = rs[rs.banco == "Bradesco"]
bad = 0
for _, r in brad.iterrows():
    if r.fech_detectado is not None and r.abertura_prox is not None:
        d = abs(r.fech_detectado - r.abertura_prox)
        if d >= 1.0:
            bad += 1
            print(f"  {r.periodo} {r.titular}: fech={brl(r.fech_detectado)} vs prox_abertura={brl(r.abertura_prox)} dif={brl(r.fech_detectado-r.abertura_prox)}")
print(f"  cadeia Bradesco: {'TODAS OK' if bad==0 else str(bad)+' divergencias'}")
