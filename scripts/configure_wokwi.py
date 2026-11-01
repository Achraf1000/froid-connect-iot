"""Generate ignored local config with verified TLS CA; do not print device keys."""
import argparse
import re
import socket
import ssl
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import certifi
import httpx
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def find_trusted_ca(host):
    """Pin the issuing CA from a fully verified chain to reduce ESP32 TLS work."""
    context = ssl.create_default_context(cafile=certifi.where())
    with socket.create_connection((host, 443), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=host) as tls:
            chain = tls._sslobj.get_verified_chain()
            if len(chain) < 2:
                raise RuntimeError("La chaine HTTPS verifiee ne contient pas de CA.")
            issuer_pem = chain[1].public_bytes()
            if isinstance(issuer_pem, str):
                issuer_pem = issuer_pem.encode()
    issuer = x509.load_pem_x509_certificate(issuer_pem)
    if not issuer.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
        raise RuntimeError("Le certificat selectionne n'est pas une autorite de confiance.")
    return issuer.public_bytes(Encoding.PEM).decode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--transport", default="TRIP-DEMO-001")
    args = parser.parse_args()
    url = args.url
    if not url:
        tunnels = httpx.get("http://127.0.0.1:4040/api/tunnels").json()["tunnels"]
        url = next(t["public_url"] for t in tunnels if t["public_url"].startswith("https://"))
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.path not in ("", "/") or parsed.username or parsed.password:
        raise ValueError("Une origine HTTPS sans chemin ni identifiant est requise.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.transport):
        raise ValueError("Identifiant de transport invalide.")
    httpx.get(url.rstrip("/") + "/health", headers={"ngrok-skip-browser-warning": "1"}, timeout=15).raise_for_status()
    ca = find_trusted_ca(parsed.hostname)
    config = dotenv_values(ROOT / ".env")
    text = (
        '#pragma once\n'
        f'constexpr char API_BASE_URL[] = "{url.rstrip("/")}";\n'
        f'constexpr char DEVICE_API_KEY[] = "{config["DEVICE_API_KEY"]}";\n'
        f'constexpr char TRANSPORT_ID[] = "{args.transport}";\n'
        f'constexpr char ROOT_CA[] = R"CERT({ca})CERT";\n'
    )
    (ROOT / "firmware/coldchain_config.h").write_text(text, encoding="utf-8")
    archive = ROOT / ".runtime/wokwi-import.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("sketch.ino", "diagram.json", "libraries.txt", "coldchain_config.h"):
            z.write(ROOT / "firmware" / name, name)
    (ROOT / ".runtime/tunnel-url.txt").write_text(url, encoding="utf-8")
    print("Configuration Wokwi et archive locale générées. Clé non affichée.")


if __name__ == "__main__":
    main()
