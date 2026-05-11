# 🔍 LeakRadar Tools

> **AVISO LEGAL:** Use apenas em ativos com autorização legal. A coleta não autorizada de dados pode violar a LGPD, o Marco Civil da Internet e legislações correlatas.

Coleção de scripts Python para automação de coleta e análise de credenciais vazadas via **[API do LeakRadar.io](https://leakradar.io)** — plataforma que indexa 290B+ credenciais de stealer logs e combolists.

---

## 📦 Instalação

```bash
pip install leakradar
```

## 🔑 Autenticação

Defina seu token como variável de ambiente ou passe via `--token`:

```bash
export LEAKRADAR_TOKEN="seu_token_aqui"
```

---

## 📜 Scripts

### 1. `search_email_bulk.py` — Busca por E-mail

Busca e desbloqueio de credenciais por e-mail (individual ou bulk via arquivo).

```bash
# Busca simples
python search_email_bulk.py --email alvo@empresa.com.br

# Lista de e-mails
python search_email_bulk.py --file emails.txt

# Com desbloqueio de senhas (consome créditos)
python search_email_bulk.py --email alvo@empresa.com.br --unlock --max-leaks 200
```

| Flag | Descrição |
|---|---|
| `--email` | E-mail único |
| `--file` | Arquivo `.txt` com lista de e-mails |
| `--unlock` | Desbloqueia senhas (**consome créditos**) |
| `--max-leaks` | Máx. de leaks a desbloquear (padrão: 100) |
| `--page-size` | Registros por página (padrão: 50) |
| `--token` | Token da API |

---

### 2. `domain_recon.py` — Reconhecimento de Domínio

Coleta employees, customers e third-parties expostos. Suporta batch check de até 100 domínios.

```bash
# Recon completo
python domain_recon.py --domain empresa.com.br

# Apenas employees com desbloqueio
python domain_recon.py --domain empresa.com.br --category employees --unlock

# Batch check (sem desbloquear)
python domain_recon.py --file dominios.txt --batch-check
```

| Flag | Descrição |
|---|---|
| `--domain` | Domínio único |
| `--file` | Arquivo `.txt` com lista de domínios |
| `--category` | `all` \| `employees` \| `customers` \| `third_parties` |
| `--unlock` | Desbloqueia leaks (**consome créditos**) |
| `--batch-check` | Verifica existência de exposição em bulk |
| `--token` | Token da API |

---

### 3. `advanced_search.py` — Busca Avançada

Usa o endpoint `search_advanced` (POST) com filtros combinados. Suporta desbloqueio em massa via `unlock_all_advanced`.

```bash
# Por domínio de e-mail
python advanced_search.py --email-domain empresa.com.br

# Por URL infectada + intervalo de datas
python advanced_search.py --url-domain empresa.com.br --added-from 2024-01-01

# Desbloqueio em massa
python advanced_search.py --email-domain empresa.com.br --unlock --max-leaks 1000
```

| Flag | Descrição |
|---|---|
| `--email-domain` | Domínio de e-mail |
| `--url-domain` | Domínio de URL infectada |
| `--username` | Username exato |
| `--password` | Senha exata |
| `--is-email` | Apenas entradas onde username é e-mail |
| `--added-from` | Data inicial `YYYY-MM-DD` |
| `--added-to` | Data final `YYYY-MM-DD` |
| `--unlock` | Desbloqueio em massa (**consome créditos**) |
| `--max-leaks` | Máx. a desbloquear (padrão: 500) |
| `--token` | Token da API |

---

## 📄 Campos do CSV

Todos os scripts exportam CSV com timestamp no nome (`leakradar_<modo>_<alvo>_YYYYMMDD_HHMMSS.csv`):

| Campo | Descrição |
|---|---|
| `email` | Endereço de e-mail |
| `email_domain` | Domínio do e-mail |
| `username` | Username da credencial |
| `password` | Senha (vazia se não desbloqueada) |
| `url` | URL completa do site infectado |
| `url_domain` | Domínio do site infectado |
| `is_email` | `True` se username é e-mail |
| `unlocked` | `True` se senha foi desbloqueada |
| `added_at` | Data de inclusão no índice |
| `id` | ID único do registro |

---

## ⚠️ Tratamento de Erros

Todos os scripts tratam os erros da API LeakRadar:

- `UnauthorizedError` — token inválido
- `PaymentRequiredError` — créditos insuficientes
- `TooManyRequestsError` — rate limit (aguarda 60s automaticamente)
- `LeakRadarAPIError` — erros gerais de API

---

## 📋 Requisitos

```
python >= 3.10
leakradar
```

---

## 📝 Licença

MIT — uso por sua conta e risco. **Apenas para fins legítimos e autorizados.**
