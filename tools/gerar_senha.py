# -*- coding: utf-8 -*-
"""Gera o bloco (salt+hash) de uma senha p/ colar em config/usuarios.yaml.

Uso:
    py tools/gerar_senha.py <senha> <usuario> "<Nome exibido>"

Ex.:
    py tools/gerar_senha.py "MinhaSenhaForte#2026" sabrina "Sabrina"

Cole a saída dentro de 'usuarios:' no arquivo config/usuarios.yaml.
A senha NÃO é guardada em lugar nenhum — só o salt e o hash (irreversível).
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import auth

if len(sys.argv) < 2:
    print('Uso: py tools/gerar_senha.py <senha> <usuario> "<Nome>"')
    sys.exit(1)

senha = sys.argv[1]
user = (sys.argv[2] if len(sys.argv) > 2 else "usuario").strip().lower()
nome = sys.argv[3] if len(sys.argv) > 3 else user
salt, h = auth.hash_senha(senha)

print("# --- cole isto dentro de 'usuarios:' em config/usuarios.yaml ---")
print(f"  {user}:")
print(f'    nome: "{nome}"')
print(f'    salt: "{salt}"')
print(f'    hash: "{h}"')
