"""Manda uma mensagem de teste no Discord pra validar o webhook."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

webhook = os.getenv("DISCORD_WEBHOOK", "").strip()
user_id = os.getenv("DISCORD_USER_ID", "").strip()

if not webhook or "cole_" in webhook:
    raise SystemExit("Configure DISCORD_WEBHOOK no arquivo .env primeiro.")

mencao = f"<@{user_id}> " if user_id else ""
r = requests.post(webhook, json={"content": f"{mencao}teste funcionando!"}, timeout=10)
print("Status:", r.status_code)
