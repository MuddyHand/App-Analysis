"""
Fase 0 — Teste exploratório de acesso à API oficial da Veo (api.veo.co).

AVISO IMPORTANTE:
A documentação pública da API da Veo é escassa. Este script NÃO assume que
os endpoints abaixo estão corretos — são hipóteses baseadas em padrões REST
comuns (equivalentes a /me, /recordings, /matches). O objetivo é correr
isto, inspecionar as respostas reais (guardadas em fase0_api/output/) e
ajustar os endpoints/autenticação em conjunto, endpoint a endpoint.

Não corras este script sem antes preencher o .env (ver .env.example na
raiz do projeto) com uma das seguintes credenciais:
  - VEO_API_TOKEN (token de acesso já emitido), ou
  - VEO_CLIENT_ID + VEO_CLIENT_SECRET (para tentar um fluxo OAuth2
    client_credentials — também especulativo).

Uso:
    python fase0_api/test_veo_api_access.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("VEO_API_BASE_URL", "https://api.veo.co").rstrip("/")
TOKEN = os.getenv("VEO_API_TOKEN", "").strip()
CLIENT_ID = os.getenv("VEO_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("VEO_CLIENT_SECRET", "").strip()

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Endpoints candidatos a testar — especulativos, ajustar após a primeira corrida.
CANDIDATE_ENDPOINTS = [
    "/me",
    "/users/me",
    "/recordings",
    "/matches",
    "/videos",
]


def try_client_credentials_flow() -> str | None:
    """Tenta um fluxo OAuth2 client_credentials para obter um token.
    Especulativo — a Veo pode não usar este esquema. Ajustar consoante
    o que a resposta real revelar (ou remover se a Veo usar API key simples)."""
    if not (CLIENT_ID and CLIENT_SECRET):
        return None

    token_url = f"{BASE_URL}/oauth/token"
    print(f"[auth] A tentar client_credentials em {token_url} ...")
    try:
        resp = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"[auth] Falhou a ligação a {token_url}: {exc}")
        return None

    save_response("oauth_token", token_url, resp)

    if resp.ok:
        try:
            data = resp.json()
            token = data.get("access_token")
            if token:
                print("[auth] Token obtido via client_credentials.")
                return token
        except ValueError:
            pass

    print(f"[auth] client_credentials não devolveu token utilizável (status {resp.status_code}).")
    return None


def save_response(label: str, url: str, resp: requests.Response) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_label = label.strip("/").replace("/", "_") or "root"
    out_path = OUTPUT_DIR / f"{timestamp}__{safe_label}.json"

    try:
        body = resp.json()
    except ValueError:
        body = resp.text

    record = {
        "url": url,
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "body": body,
    }
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return out_path


def probe_endpoint(path: str, token: str) -> None:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    print(f"\n[GET] {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as exc:
        print(f"  Falhou a ligação: {exc}")
        return

    out_path = save_response(path, url, resp)
    print(f"  status={resp.status_code}  (resposta bruta guardada em {out_path})")

    try:
        pretty = json.dumps(resp.json(), indent=2, ensure_ascii=False)
        preview = pretty[:1500]
        print(preview + ("... [truncado, ver ficheiro]" if len(pretty) > 1500 else ""))
    except ValueError:
        preview = resp.text[:500]
        print(f"  (resposta não é JSON) {preview}")


def main() -> int:
    token = TOKEN
    if not token:
        token = try_client_credentials_flow() or ""

    if not token:
        print(
            "Sem credenciais utilizáveis. Preenche VEO_API_TOKEN ou "
            "VEO_CLIENT_ID/VEO_CLIENT_SECRET no .env antes de correr este script.\n"
            "Ver fase0_api/README.md para o que é preciso pedir à Veo."
        )
        return 1

    print(f"Base URL: {BASE_URL}")
    print(f"A testar {len(CANDIDATE_ENDPOINTS)} endpoints candidatos...\n")

    for path in CANDIDATE_ENDPOINTS:
        probe_endpoint(path, token)

    print(
        f"\nConcluído. Respostas brutas em {OUTPUT_DIR}/ — "
        "inspeciona os JSON e reporta o que encontrares para ajustarmos os endpoints."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
