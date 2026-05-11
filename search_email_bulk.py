#!/usr/bin/env python3
"""
LeakRadar — Busca e desbloqueio por e-mail (individual ou bulk)
AVISO: Use apenas em ativos com autorização legal.
"""

import asyncio
import csv
import argparse
import os
import sys
from datetime import datetime

try:
    from leakradar.client import LeakRadarClient
    from leakradar.exceptions import (
        LeakRadarAPIError, TooManyRequestsError,
        UnauthorizedError, PaymentRequiredError,
    )
except ImportError:
    print("\033[91m[ERR]\033[0m Instale o wrapper: pip install leakradar")
    sys.exit(1)

INFO  = "\033[94m[INFO]\033[0m"
OK    = "\033[92m[OK]\033[0m"
WARN  = "\033[93m[WARN]\033[0m"
ERR   = "\033[91m[ERR]\033[0m"

FIELDNAMES = ["email", "email_domain", "username", "password",
              "url", "url_domain", "is_email", "unlocked", "added_at", "id"]

def csv_name(alvo: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = alvo.replace("@", "_at_").replace(".", "_")
    return f"leakradar_email_{safe}_{ts}.csv"

def normalize(leak: dict) -> dict:
    return {f: leak.get(f, "") for f in FIELDNAMES}

async def fetch_email(client, email: str, page_size: int):
    leaks, page = [], 1
    while True:
        print(f"{INFO} Buscando {email} — página {page}")
        result = await client.search_email(email=email, page=page, page_size=page_size)
        items = result.get("items") or result.get("results") or []
        if not items:
            break
        leaks.extend(items)
        print(f"{OK} {len(items)} registros recebidos (total acumulado: {len(leaks)})")
        if len(items) < page_size:
            break
        page += 1
    return leaks

async def unlock_email(client, email: str, max_leaks: int):
    print(f"{WARN} Desbloqueando senhas para {email} (consome créditos)…")
    result = await client.unlock_email_leaks(email=email, max_leaks=max_leaks)
    items = result.get("items") or result.get("results") or []
    print(f"{OK} {len(items)} credenciais desbloqueadas para {email}")
    return items

async def run(args):
    token = args.token or os.environ.get("LEAKRADAR_TOKEN")
    if not token:
        print(f"{ERR} Token não encontrado. Use --token ou defina LEAKRADAR_TOKEN.")
        sys.exit(1)

    emails = []
    if args.email:
        emails = [args.email.strip()]
    elif args.file:
        try:
            with open(args.file, "r") as fh:
                emails = [ln.strip() for ln in fh if ln.strip()]
        except FileNotFoundError:
            print(f"{ERR} Arquivo não encontrado: {args.file}")
            sys.exit(1)

    if not emails:
        print(f"{ERR} Informe um e-mail (--email) ou arquivo (--file).")
        sys.exit(1)

    print(f"{INFO} Total de alvos: {len(emails)}")
    output_csv = csv_name(emails[0] if len(emails) == 1 else "bulk")
    all_leaks = []

    async with LeakRadarClient(token=token) as client:
        for email in emails:
            print(f"\n{INFO} ── Processando: {email} ──")
            try:
                if args.unlock:
                    leaks = await unlock_email(client, email, args.max_leaks)
                else:
                    leaks = await fetch_email(client, email, args.page_size)
                all_leaks.extend(leaks)
            except UnauthorizedError:
                print(f"{ERR} Token inválido ou sem permissão.")
                sys.exit(1)
            except PaymentRequiredError:
                print(f"{WARN} Créditos insuficientes para {email}. Pulando.")
            except TooManyRequestsError:
                print(f"{WARN} Rate limit atingido. Aguardando 60s…")
                await asyncio.sleep(60)
            except LeakRadarAPIError as exc:
                print(f"{ERR} Erro de API para {email}: {exc}")

    if not all_leaks:
        print(f"{WARN} Nenhum resultado encontrado.")
        sys.exit(0)

    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for leak in all_leaks:
            writer.writerow(normalize(leak))

    print(f"\n{OK} {len(all_leaks)} registros exportados → {output_csv}")

parser = argparse.ArgumentParser(
    description="LeakRadar — Busca por e-mail | AVISO: Use apenas em ativos com autorização legal.",
)
parser.add_argument("--email",      help="E-mail único a pesquisar")
parser.add_argument("--file",       help="Arquivo .txt com lista de e-mails (um por linha)")
parser.add_argument("--token",      help="Token da API (padrão: env LEAKRADAR_TOKEN)")
parser.add_argument("--unlock",     action="store_true", help="Desbloqueia senhas — CONSOME CRÉDITOS")
parser.add_argument("--max-leaks",  type=int, default=100, help="Máx. de leaks a desbloquear (padrão: 100)")
parser.add_argument("--page-size",  type=int, default=50, help="Registros por página (padrão: 50)")

args = parser.parse_args()
asyncio.run(run(args))
