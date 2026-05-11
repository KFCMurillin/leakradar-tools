#!/usr/bin/env python3
"""
LeakRadar — Reconhecimento de domínio: employees, customers, third-parties e batch check
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
              "url", "url_domain", "is_email", "unlocked", "added_at", "id", "category"]

def csv_name(mode: str, alvo: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = alvo.replace(".", "_")
    return f"leakradar_{mode}_{safe}_{ts}.csv"

def normalize(leak: dict, category: str = "") -> dict:
    row = {f: leak.get(f, "") for f in FIELDNAMES}
    row["category"] = category
    return row

async def fetch_paged(client, method, domain: str, page_size: int, **kwargs):
    leaks, page = [], 1
    while True:
        print(f"{INFO}   página {page}…")
        result = await method(domain=domain, page=page, page_size=page_size, **kwargs)
        items = result.get("items") or result.get("results") or []
        if not items:
            break
        leaks.extend(items)
        print(f"{OK}   +{len(items)} (total: {len(leaks)})")
        if len(items) < page_size:
            break
        page += 1
    return leaks

async def run(args):
    token = args.token or os.environ.get("LEAKRADAR_TOKEN")
    if not token:
        print(f"{ERR} Token não encontrado. Use --token ou defina LEAKRADAR_TOKEN.")
        sys.exit(1)

    domains = []
    if args.domain:
        domains = [args.domain.strip()]
    elif args.file:
        try:
            with open(args.file, "r") as fh:
                domains = [ln.strip() for ln in fh if ln.strip()]
        except FileNotFoundError:
            print(f"{ERR} Arquivo não encontrado: {args.file}")
            sys.exit(1)

    if not domains:
        print(f"{ERR} Informe um domínio (--domain) ou arquivo (--file).")
        sys.exit(1)

    if args.batch_check:
        async with LeakRadarClient(token=token) as client:
            print(f"{INFO} Batch check de {len(domains)} domínio(s)…")
            try:
                categories = args.categories.split(",") if args.categories else None
                result = await client.domains_locked_exists(
                    domains=domains, categories=categories, include_counts=True,
                )
                output_csv = csv_name("batch_check", domains[0])
                with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["domain", "has_leaks", "count", "categories"])
                    for entry in (result.get("results") or []):
                        writer.writerow([
                            entry.get("domain", ""),
                            entry.get("exists", ""),
                            entry.get("count", ""),
                            ";".join(entry.get("categories", [])),
                        ])
                print(f"{OK} Resultado exportado → {output_csv}")
            except LeakRadarAPIError as exc:
                print(f"{ERR} {exc}")
        return

    all_leaks = []
    output_csv = csv_name("domain", domains[0] if len(domains) == 1 else "bulk")

    async with LeakRadarClient(token=token) as client:
        for domain in domains:
            print(f"\n{INFO} ══ Domínio: {domain} ══")
            categories_to_fetch = {
                "employees":     client.get_domain_employees,
                "customers":     client.get_domain_customers,
                "third_parties": client.get_domain_third_parties,
            }
            requested = (
                [args.category] if args.category and args.category != "all"
                else list(categories_to_fetch.keys())
            )
            for cat in requested:
                if cat not in categories_to_fetch:
                    print(f"{WARN} Categoria inválida ignorada: {cat}")
                    continue
                print(f"{INFO} Categoria: {cat}")
                try:
                    leaks = await fetch_paged(client, categories_to_fetch[cat], domain, args.page_size)
                    for leak in leaks:
                        all_leaks.append(normalize(leak, cat))
                except TooManyRequestsError:
                    print(f"{WARN} Rate limit. Aguardando 60s…")
                    await asyncio.sleep(60)
                except PaymentRequiredError:
                    print(f"{WARN} Créditos insuficientes para {cat}/{domain}. Pulando.")
                except UnauthorizedError:
                    print(f"{ERR} Token inválido.")
                    sys.exit(1)
                except LeakRadarAPIError as exc:
                    print(f"{ERR} {exc}")

            if args.unlock:
                print(f"{WARN} Desbloqueando leaks de {domain} (consome créditos)…")
                try:
                    leak_type = args.category if args.category != "all" else "employees"
                    result = await client.unlock_domain_leaks(
                        domain=domain, leak_type=leak_type, max_leaks=args.max_leaks
                    )
                    unlocked = result.get("items") or result.get("results") or []
                    print(f"{OK} {len(unlocked)} credenciais desbloqueadas")
                    for leak in unlocked:
                        all_leaks.append(normalize(leak, f"{leak_type}_unlocked"))
                except (PaymentRequiredError, TooManyRequestsError, LeakRadarAPIError) as exc:
                    print(f"{WARN} Desbloqueio falhou: {exc}")

    if not all_leaks:
        print(f"{WARN} Nenhum resultado encontrado.")
        sys.exit(0)

    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_leaks)

    print(f"\n{OK} {len(all_leaks)} registros exportados → {output_csv}")

parser = argparse.ArgumentParser(
    description="LeakRadar — Recon de domínio | AVISO: Use apenas em ativos com autorização legal.",
)
parser.add_argument("--domain",      help="Domínio único alvo")
parser.add_argument("--file",        help="Arquivo .txt com lista de domínios")
parser.add_argument("--token",       help="Token da API")
parser.add_argument("--category",    default="all",
                    choices=["all", "employees", "customers", "third_parties"])
parser.add_argument("--unlock",      action="store_true", help="Desbloqueia leaks — CONSOME CRÉDITOS")
parser.add_argument("--max-leaks",   type=int, default=200)
parser.add_argument("--page-size",   type=int, default=50)
parser.add_argument("--batch-check", action="store_true")
parser.add_argument("--categories",  help="Filtro de categorias para batch-check (vírgula separado)")

args = parser.parse_args()
asyncio.run(run(args))
