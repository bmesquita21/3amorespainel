# 🚀 Migração para VPS Debian (Docker + Portainer + Nginx) com GitHub — guia do TI

Colocar o **Painel Financeiro 3 Amores** no VPS **Debian** já existente, usando **Docker/Portainer**,
o **Nginx** atual como proxy/HTTPS, **GitHub** para o código e **deploy automático** (Portainer GitOps).
Os **dados** vêm de uma **pasta SMB**.

> ⚠️ **SEGURANÇA (inegociável):** repositório **PRIVADO**. Dados bancários e senhas **NÃO** vão pro git
> (há `.gitignore` + `.dockerignore` que os excluem). Eles vivem **só na pasta SMB**.

---

## 1. Arquitetura
```
 GitHub (repo privado)        Portainer (GitOps)            Container painel-3amores         Nginx (já existe)
 ┌────────────────────┐  pull  ┌──────────────────┐  build  ┌────────────────────────┐  proxy ┌──────────────┐
 │ app/ tools/ config/ │ ─────▶ │ stack (compose)  │ ──────▶ │ streamlit :8501 (interno)│ ◀───── │ HTTPS + domínio│
 │ Dockerfile          │ auto   └──────────────────┘         │ PAINEL_DADOS=/dados      │        └──────────────┘
 │ docker-compose.yml  │                                     └───────────┬────────────┘
 └────────────────────┘                                        volume    │ /mnt/dados-painel (SMB do host)
        CÓDIGO                                                            ▼  DADOS + SENHAS (nunca no git)
```
- **GitHub** = código + `Dockerfile` + `docker-compose.yml`.
- **Portainer** = sobe a stack a partir do repo Git e **atualiza sozinho** quando há push (GitOps).
- **Container** = roda o Streamlit na porta interna 8501.
- **Nginx** (atual) = proxy + HTTPS para o container.
- **SMB** = planilhas/extratos + `config/` (de-para + `usuarios.yaml` + correções). Montada no host e mapeada para `/dados`.

## 2. Repositório (uma vez)
```bash
git init && git add . && git commit -m "Painel 3 Amores - inicial"
git branch -M main
git remote add origin git@github.com:GRUPO/painel-3amores.git
git push -u origin main
```
Confira no GitHub que **não** subiram PDFs de extrato, planilhas nem `usuarios.yaml` (o `.gitignore` cuida).

## 3. Pasta SMB (dados) — montar no host Debian
```bash
sudo mkdir -p /mnt/dados-painel
# /etc/fstab (montagem permanente):
//servidor/painel-dados /mnt/dados-painel cifs credentials=/etc/smb-painel.cred,uid=1000,gid=1000,iocharset=utf8,file_mode=0664,dir_mode=0775 0 0
sudo mount -a
```
**Estrutura dentro da SMB** (a Sabrina larga as planilhas aqui — mesma estrutura de hoje):
```
/mnt/dados-painel/
  config/            <- copie o config/ do repo aqui + gere o usuarios.yaml aqui
  0 COMPOSIÇÕES.../  1.1 FLUXO.../  1.2 FLUXO.../  1.3 EXTRATO/
  2.1 DRE.../  2.2 DRE.../  3 LEVANTAMENTO.../  4 PRODUTOS.../  RECRIA.../
```
Copiar de-para + gerar senhas reais (uma vez):
```bash
cp -r ./config /mnt/dados-painel/        # de-para inicial
python tools/gerar_senha.py "SenhaForte#2026" sabrina "Sabrina"   # cole em /mnt/dados-painel/config/usuarios.yaml
```

## 4. Subir a stack no Portainer (GitOps = deploy automático)
1. **Portainer → Stacks → Add stack → Build method: Repository**.
2. Repository URL = o repo GitHub (privado → cadastrar credencial/*deploy key*).
3. Compose path = `docker-compose.yml`.
4. Ative **"Automatic updates"** → **Webhook** (cole o webhook nas *Settings → Webhooks* do GitHub) **ou** *Polling* (ex.: 5 min).
5. **Ajuste no `docker-compose.yml`** (pode editar direto no Portainer):
   - `volumes:` o caminho do host da SMB (ex.: `/mnt/dados-painel:/dados`).
   - `networks:` o nome da **rede Docker do seu Nginx** (ex.: `nginx_proxy`, `npm_default`, `traefik`).
6. **Deploy the stack.** Pronto — a cada `git push`, o Portainer recompila e sobe a versão nova.

## 5. Nginx (já existe) → proxy + HTTPS
Aponte um subdomínio (ex.: `painel.grupobomjardim.com.br`) para o container `painel-3amores:8501`.
**Streamlit usa WebSocket** — inclua no proxy:
```nginx
location / {
    proxy_pass http://painel-3amores:8501;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400;
}
```
Certificado TLS (Let's Encrypt). **Recomendado:** manter atrás da **VPN** da empresa; a tela de **login** do app é a 2ª camada.

## 6. Fluxo do dia a dia
- **Novos dados** (planilhas/extratos): Sabrina larga na **pasta SMB** → no painel, botão **🔄 Atualizar**.
- **Mudança de código** (nova função/correção): `git push` → Portainer redeploya sozinho.
- **Correções de classificação**: a Sabrina faz pelo painel → salvam na SMB (`config/correcoes_classificacao.csv`).

## 7. Observações
- **Supabase** (que você já tem) **não é necessário** para o painel atual — ele lê arquivos, não banco. *(Evolução futura: migrar os dados para o Supabase/Postgres em vez de planilhas — projeto à parte.)*
- **`.github/workflows/deploy.yml`** (no repo) é uma **alternativa** ao GitOps do Portainer (deploy via SSH). Se usar o Portainer GitOps (item 4), **pode ignorar/excluir** esse arquivo.
- Build local p/ testar antes: `docker compose up -d --build` (com a SMB montada).

## ✅ Checklist
- [ ] Repo **PRIVADO**; sem dados/senhas no GitHub
- [ ] SMB montada no host (fstab) com `config/` + subpastas + permissões de escrita p/ a Sabrina
- [ ] `usuarios.yaml` gerado **na SMB** (senha real, não a provisória `trocar@2026`)
- [ ] Stack no Portainer via **Repository** + **Automatic updates** ligado
- [ ] `docker-compose.yml` ajustado: caminho da SMB + rede do Nginx
- [ ] Nginx com **HTTPS** + headers de WebSocket; firewall fechando a porta
- [ ] Push de teste → Portainer redeployou automaticamente
