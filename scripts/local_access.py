from pathlib import Path

from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
config = dotenv_values(root / ".env")
(root / ".runtime").mkdir(exist_ok=True)
(root / ".runtime/acces-local.txt").write_text(
    "FROID CONNECT — Accès local privé\n"
    "Adresse : http://127.0.0.1:8000\n"
    f"Mot de passe : {config['DASHBOARD_PASSWORD']}\n\n"
    "Ce fichier contient votre mot de passe local. Ne pas publier ni ajouter à Git.\n",
    encoding="utf-8",
)
print("Accès local enregistré dans .runtime/acces-local.txt ; mot de passe non affiché.")
