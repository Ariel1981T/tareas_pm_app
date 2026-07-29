"""
ALTERNATIVA a obtener_token.py, para cuando Google Cloud Console no
muestra el botón de "Descargar JSON" en tu vista.

Qué hace: arma el archivo client_secret.json por ti, a partir de 2
valores que copias directamente de la página de detalle de tu ID de
cliente en Google Cloud Console (con el ícono de portapapeles junto a
cada uno, para evitar errores de transcripción).

Pega tus valores en las 2 líneas marcadas abajo y luego corre:
    python3 armar_credenciales.py
Esto crea client_secret.json listo para que obtener_token.py lo use.
"""

import json

# --- PEGA AQUÍ, entre las comillas, lo que copiaste con el ícono de portapapeles ---
CLIENT_ID = "PEGA-AQUI-EL-CLIENT-ID-COMPLETO.apps.googleusercontent.com"
CLIENT_SECRET = "PEGA-AQUI-EL-CLIENT-SECRET-COMPLETO"
# -------------------------------------------------------------------------------

contenido = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

if "PEGA-AQUI" in CLIENT_ID or "PEGA-AQUI" in CLIENT_SECRET:
    print("\nERROR: todavía tienes los placeholders sin reemplazar.")
    print("Abre este archivo, pega tu Client ID y Client Secret reales "
          "en las líneas marcadas, y vuelve a correr.\n")
    raise SystemExit(1)

with open("client_secret.json", "w") as f:
    json.dump(contenido, f, indent=2)

print("\nListo: se creó client_secret.json")
print(f"Client ID guardado: {CLIENT_ID}")
print("Ahora corre: python3 obtener_token.py\n")
