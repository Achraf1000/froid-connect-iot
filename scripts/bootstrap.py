"""Create isolated development configuration; never print credentials."""
import hashlib
import json
import secrets
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def setup():
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    env = ROOT / ".env"
    if not env.exists():
        template = (ROOT / ".env.example").read_text(encoding="utf-8")
        template = template.replace("replace-with-a-random-device-key", secrets.token_urlsafe(32))
        template = template.replace("replace-with-a-local-password", secrets.token_urlsafe(18))
        template = template.replace("replace-with-a-random-session-key", secrets.token_urlsafe(48))
        env.write_text(template, encoding="utf-8")
        print("Configuration locale créée dans .env (secrets non affichés).")
    tools = ROOT / ".tools"
    tools.mkdir(exist_ok=True)
    marker = tools / "node-path.txt"
    if not marker.exists():
        index = json.load(urllib.request.urlopen("https://nodejs.org/dist/index.json"))
        version = next(v["version"] for v in index if v["version"].startswith("v24."))
        name = f"node-{version}-win-x64"
        archive = tools / f"{name}.zip"
        url = f"https://nodejs.org/dist/{version}/"
        print(f"Téléchargement isolé de Node.js {version}…")
        urllib.request.urlretrieve(url + archive.name, archive)
        sums = urllib.request.urlopen(url + "SHASUMS256.txt").read().decode()
        expected = next(line.split()[0] for line in sums.splitlines() if line.endswith("  " + archive.name))
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Checksum Node.js incorrect.")
        with zipfile.ZipFile(archive) as z:
            z.extractall(tools)
        marker.write_text(str(tools / name), encoding="utf-8")
        print("Node.js installé dans .tools ; installation globale conservée.")


if __name__ == "__main__":
    setup()
