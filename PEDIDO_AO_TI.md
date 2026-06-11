# 📩 Pedido ao TI — Publicar o Painel Financeiro 3 Amores

*(Sabrina → equipe de TI do Grupo Bom Jardim. Pode encaminhar este arquivo.)*

## Objetivo
Colocar o **Painel Financeiro 3 Amores** disponível **24/7** e acessível **pela internet, de qualquer lugar**, para **4 pessoas** (Sabrina, 2 sócios, contabilidade), com **segurança** (contém dados financeiros e bancários).

## O que estou entregando pra vocês
1. A **pasta do projeto** inteira (`3 Amores CODE - ATUALIZADO`).
2. O **guia técnico** com todo o passo a passo: **`DEPLOY_GUIA_TI.md`** (na raiz do projeto).
3. A lista de dependências: `requirements.txt`.

## O que preciso que vocês façam (resumo)
1. **Instalar** o app no servidor da empresa (é **Python 3.12 + Streamlit**; passos no guia, §3-§4).
2. **Deixar rodando 24/7** como serviço — não pode depender de um PC ligado (guia §6).
3. **Criar o endereço de acesso pela internet** (escolher A ou B abaixo).
4. **Segurança obrigatória** (guia §7): **HTTPS** (cadeado) + **firewall** bloqueando a porta crua. A **tela de login** já vem pronta no app (4 usuários).
5. **Criar uma pasta de dados compartilhada** que eu acesse pra atualizar as planilhas (guia §9).

## ⚠️ Decisão de vocês: COMO expor o acesso
Pra "qualquer um acessar de onde estiver", há 2 caminhos — me digam qual preferem:

| | **A) Endereço público + HTTPS** | **B) Acesso pela VPN da empresa** |
|---|---|---|
| Como acessa | `https://painel.grupobomjardim.com.br` de qualquer internet | Conecta na VPN, depois abre o painel |
| Praticidade p/ os 4 usuários | ✅ só abrir o link | requer VPN instalada em cada dispositivo |
| Segurança | Boa (HTTPS + login), mas exposto na internet | ✅ Melhor (não fica exposto) |
| Precisa | Subdomínio + certificado HTTPS + reverse proxy | A VPN que a empresa já tem |

> **Recomendação:** se a empresa já tem **VPN**, usem a **opção B** (mais seguro p/ dados bancários). Se preferirem o link aberto (opção A), tudo bem — mas aí o **HTTPS é inegociável** e a tela de login fica como 2ª camada.

## Senhas
- O app já vem com 4 logins; **senha provisória de todos = `trocar@2026`**.
- **Precisamos trocar** por senhas de verdade no go-live (instruções no guia §8 — comando `tools/gerar_senha.py`).

## Em uma frase
> "Instalar o painel no servidor, deixar 24/7, expor com **HTTPS ou VPN**, e me dar uma **pasta compartilhada** pra atualizar os dados. Detalhes técnicos no `DEPLOY_GUIA_TI.md`."
