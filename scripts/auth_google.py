"""
Google Workspace OAuth 2.0 Token Generator for Lilo Hub.
Generates token.json from credentials.json for Calendar & Gmail access.
"""
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

def main():
    if not CREDENTIALS_FILE.exists():
        print(f"Error: {CREDENTIALS_FILE} no encontrado.")
        return

    print("Iniciando flujo de autenticación OAuth de Google...")
    print(f"Leyendo credenciales desde: {CREDENTIALS_FILE}")
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES
    )
    
    # Run local server to catch OAuth redirect
    creds = flow.run_local_server(port=0, open_browser=True)
    
    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())
    
    print(f"¡Éxito! Token guardado correctamente en: {TOKEN_FILE}")

if __name__ == "__main__":
    main()
