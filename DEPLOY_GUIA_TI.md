# 🖥️ Guia de Publicação — Painel Financeiro 3 Amores (para o TI)

Documento para a equipe de TI do Grupo Bom Jardim colocar o **Painel Financeiro 3 Amores**
no ar **24/7**, acessível pela internet **com segurança** (dados financeiros e bancários).

Usuários previstos: **4** (Sabrina, 2 sócios, contabilidade). Volume baixo.

---

## 1. O que é
- App **Python 3.12 + Streamlit** (servidor web local na porta **8501**).
- Lê planilhas/PDF de uma pasta de dados, calcula DRE / Fluxo de Caixa / Balanço e mostra no navegador.
- **Stateless** quanto a banco de dados: não usa BD; lê os arquivos da pasta a cada "Atualizar".

## 2. Pré-requisitos no servidor
- **Python 3.12** (64 bits).
- Acesso à internet para instalar pacotes (ou um índice pip interno).
- ~500 MB de disco para libs + o tamanho da pasta de dados.

## 3. Instalação
```bat
:: 1) copie a pasta do projeto para o servidor, ex.: C:\apps\painel-3amores
cd /d C:\apps\painel-3amores

:: 2) (recomendado) ambiente virtual isolado
py -m venv .venv
.venv\Scripts\activate

:: 3) instale as dependências
py -m pip install -r requirements.txt
```

## 4. Teste rápido (foreground)
```bat
py -m streamlit run app\painel.py
```
Abra `http://localhost:8501`. Deve aparecer a **tela de login**. (Linux: `python3 -m streamlit run app/painel.py`.)

## 5. Configuração de produção
Já existe **`.streamlit/config.toml`** no projeto. Revise:
```toml
[server]
headless = true
address = "127.0.0.1"   # só local; quem expõe é o reverse proxy (item 7). Use 0.0.0.0 só se NÃO houver proxy.
port = 8501
enableXsrfProtection = true
enableCORS = false
maxUploadSize = 50
[browser]
gatherUsageStats = false
```

## 6. Deixar 24/7 (rodar como serviço)
**Windows Server (NSSM — recomendado):**
```bat
:: baixe o NSSM (nssm.cc) e:
nssm install Painel3Amores "C:\apps\painel-3amores\.venv\Scripts\python.exe" "-m streamlit run app\painel.py"
nssm set Painel3Amores AppDirectory "C:\apps\painel-3amores"
nssm set Painel3Amores Start SERVICE_AUTO_START
nssm start Painel3Amores
```
**Linux (systemd):** crie `/etc/systemd/system/painel3amores.service` com `ExecStart=/caminho/.venv/bin/python -m streamlit run app/painel.py`, `WorkingDirectory=/caminho`, `Restart=always`; depois `systemctl enable --now painel3amores`.

> Alternativa de agendador no Windows: Task Scheduler com gatilho "Ao iniciar o computador".

## 7. 🔒 Segurança (OBRIGATÓRIO — são dados bancários)
1. **HTTPS via reverse proxy** na frente do Streamlit (NUNCA exponha a 8501 crua na internet):
   - **IIS** (ARR/URL Rewrite) ou **Nginx**: encaminhe `https://painel.grupobomjardim.com.br` → `http://127.0.0.1:8501`.
   - Streamlit precisa de WebSocket: no proxy, habilite `Upgrade`/`Connection` (Nginx: `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`).
   - Certificado TLS (Let's Encrypt ou o da empresa).
2. **Preferência forte: deixar atrás da VPN da empresa** (acesso só por quem está na VPN). Aí o link nem precisa ser público.
3. **Firewall:** bloquear a porta 8501 de fora; só o proxy/VPN acessa.
4. **Login do app** (já incluso): ver item 8. É a 2ª camada — não substitui HTTPS/VPN.

## 8. Usuários e senhas (login do app)
- Arquivo: **`config/usuarios.yaml`** — guarda **hash PBKDF2** (nunca a senha em texto).
- Já vem com 4 contas: `sabrina`, `alvaro`, `socio2`, `contabil`.
- **⚠️ Senha provisória de todos = `trocar@2026`. TROQUE no primeiro acesso.**
- Trocar/criar senha:
  ```bat
  py tools\gerar_senha.py "NovaSenhaForte#2026" sabrina "Sabrina"
  ```
  Copie o bloco impresso e cole no lugar do usuário em `config/usuarios.yaml`. Reinicie o serviço.
- Remover um usuário: apague o bloco dele do yaml.
- **Proteja o `usuarios.yaml`** (permissão de leitura só pela conta do serviço). Não compartilhe.

## 9. Pasta de dados (como a Sabrina atualiza os números)
- Por padrão o painel lê a **própria pasta do projeto** (campo "Pasta de dados" na barra lateral).
- **Recomendado:** crie uma **pasta compartilhada** no servidor (ex.: `\\servidor\painel-dados`) com a mesma estrutura de subpastas (`2.1 DRE...`, `2.2 DRE...`, `1.3 EXTRATO`, etc.).
  - Mapeie como unidade de rede no PC da Sabrina; ela larga as planilhas lá.
  - No painel, aponte o campo "Pasta de dados" para esse caminho e clique **🔄 Atualizar**.
- Permissão: a Sabrina (e quem atualiza) precisa de **escrita** na pasta; o serviço precisa de **leitura**.

## 10. Atualizar o código do painel (quando a Sabrina/Claude mandar versão nova)
1. Pare o serviço (`nssm stop Painel3Amores`).
2. Substitua os arquivos da pasta `app\` (e `config\` se mudou).
3. `py -m pip install -r requirements.txt` (caso novas libs).
4. Inicie o serviço.
> O `iniciar.bat` já limpa `app\__pycache__` ao subir; no serviço, garanta o mesmo (apagar `app\__pycache__` no deploy) para evitar bytecode antigo.

## 11. Backup
- Faça backup da **pasta de dados** e do **`config/`** (de-para + usuarios.yaml). O resto é código (versionável).

## 12. ✅ Checklist de go-live
- [ ] Python 3.12 + `requirements.txt` instalados em venv
- [ ] App sobe e mostra a tela de login
- [ ] Serviço 24/7 configurado (NSSM/systemd) com auto-start
- [ ] Reverse proxy com **HTTPS** OU acesso só por **VPN**
- [ ] Porta 8501 **bloqueada** de fora pelo firewall
- [ ] Senhas provisórias **trocadas**; `usuarios.yaml` protegido
- [ ] Pasta de dados compartilhada + permissões certas
- [ ] Teste de acesso externo por um dos sócios

---

**Contato do projeto:** Sabrina. Dúvidas técnicas do código: ver `CLAUDE.md` na raiz do projeto.
