# -*- coding: utf-8 -*-
"""Diagnostico: qual processo responde na 8501, quando subiu, de qual pasta."""
import subprocess, re, sys
sys.stdout.reconfigure(encoding="utf-8")

out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
pids = []
for line in out.splitlines():
    if "LISTENING" in line and re.search(r":850\d\b", line):
        nums = re.findall(r"\d+", line)
        porta = re.search(r":(\d{4})\b", line)
        if nums:
            pids.append((porta.group(1) if porta else "?", nums[-1]))

print("Listeners em 850x:", pids if pids else "NENHUM")
seen = set()
for porta, pid in pids:
    if pid in seen:
        continue
    seen.add(pid)
    w = subprocess.run(["wmic", "process", "where", f"ProcessId={pid}",
                        "get", "CommandLine,CreationDate", "/value"],
                       capture_output=True, text=True).stdout
    info = {}
    for l in w.splitlines():
        if "=" in l:
            k, v = l.split("=", 1)
            info[k.strip()] = v.strip()
    cd = info.get("CreationDate", "")[:14]
    if len(cd) == 14:
        cd = f"{cd[0:4]}-{cd[4:6]}-{cd[6:8]} {cd[8:10]}:{cd[10:12]}:{cd[12:14]}"
    print(f"\n  PORTA {porta}  PID {pid}  iniciado: {cd}")
    print(f"     CMD: {info.get('CommandLine', '')[:160]}")
