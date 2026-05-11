#!/usr/bin/env python3
"""
LeakRadar — Busca avançada com filtros combinados e desbloqueio em massa
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

def csv_name(tag: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"leakradar_advanced_{tag}_{ts}.csv"

def normalize(leak: dict) -> dict:
    return {f: leak.get(f, "") for f in FIELDNAMES}

def build_filters(args) -> dict:
    filters = {}
    if args.username:      filters["username"]     = args.username
    if args.password:      filters["password"]     = args.password
    if args.email_domain:  filters["email_domain"] = args.email_domain
    if args.url_domain:    filters["url_domain"]   = args.url_domain
    if args.is_email:      filters["is_email"]     = True
    if args.added_from:    filters["added_from"]   = args.added_from
    if args.added_to:      filters["added_to"]     = args.added_to
    return filters

async def run(args):
    token = args.token or os.environ.get("LEAKRADAR_TOKEN")
    if not token:
        print(f"{ERR} Token não encontrado. Use --token ou defina LEAKRADAR_TOKEN.")
        sys.exit(1)

    filters = build_filters(args)
    if not filters:
        print(f"{ERR} Informe pelo menos um filtro.")
        sys.exit(1)

    tag = (
        args.email_domain or args.url_domain or args.username or "query"
    ).replace(".", "_").replace("@", "_at_")

    output_csv = csv_name(tag)
    all_leaks  = []

    print(f"{INFO} Filtros ativos: {filters}")

    async with LeakRadarClient(token=token) as client:
        if args.unlock:
            print(f"{WARN} Modo desbloqueio em massa ativo (consome créditos)…")
            try:
                result = await client.unlock_all_advanced(filters=filters, max_leaks=args.max_leaks)
                all_leaks = result.get("items") or result.get("results") or []
                print(f"{OK} {len(all_leaks)} credenciais desbloqueadas")
            except UnauthorizedError:
                print(f"{ERR} Token inválido."); sys.exit(1)
            except PaymentRequiredError:
                print(f"{ERR} Créditos insuficientes."); sys.exit(1)
            except TooManyRequestsError:
                print(f"{WARN} Rate limit atingido."); sys.exit(1)
            except LeakRadarAPIError as exc:
                print(f"{ERR} {exc}"); sys.exit(1)
        else:
            page = 1
            while True:
                print(f"{INFO} search_advanced — página {page}…")
                try:
                    result = await client.search_advanced(page=page, page_size=args.page_size, **filters)
                except TooManyRequestsError:
                    print(f"{WARN} Rate limit. Aguardando 60s…")
                    await asyncio.sleep(60)
                    continue
                except UnauthorizedError:
                    print(f"{ERR} Token inválido."); sys.exit(1)
                except LeakRadarAPIError as exc:
                    print(f"{ERR} {exc}"); break

                items = result.get("items") or result.get("results") or []
                if not items:
                    break
                all_leaks.extend(items)
                print(f"{OK} +{len(items)} (total: {len(all_leaks)})")
                if len(items) < args.page_size:
                    break
                page += 1

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
    description="LeakRadar — Busca avançada | AVISO: Use apenas em ativos com autorização legal.",
)
parser.add_argument("--token",        help="Token da API")
parser.add_argument("--email-domain", dest="email_domain")
parser.add_argument("--url-domain",   dest="url_domain")
parser.add_argument("--username")
parser.add_argument("--password")
parser.add_argument("--is-email",     dest="is_email", action="store_true", default=False)
parser.add_argument("--added-from",   dest="added_from")
parser.add_argument("--added-to",     dest="added_to")
parser.add_argument("--unlock",       action="store_true", help="CONSOME CRÉDITOS")
parser.add_argument("--max-leaks",    type=int, default=500)
parser.add_argument("--page-size",    type=int, default=50)

args = parser.parse_args()
asyncio.run(run(args))
