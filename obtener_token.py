"""
EJECUTAR UNA SOLA VEZ, en la computadora donde puedas abrir un navegador
con la sesión de la cuenta de Google del Project Manager (la misma que
usa para Chat y Tasks).

Qué hace:
1. Abre el navegador y pide iniciar sesión con la cuenta de Google del PM.
2. Pide autorización SOLO para leer Google Tasks (no puede escribir,
   no puede ver correo, no puede ver Drive).
3. Al terminar, imprime en pantalla 3 valores que debes copiar a
   `secrets.toml` de la app: client_id, client_secret y refresh_token.

Requiere antes:
1. Crear un "ID de cliente de OAuth" tipo "App de escritorio" en
   Google Cloud Console.
2. Descargar el JSON de esas credenciales (botón de descarga junto al
   ID de cliente en la lista de Credenciales) y guardarlo en esta misma
   carpeta con el nombre EXACTO: client_secret.json

   Usar el JSON descargado (en vez de copiar/pegar el client_id y el
   client_secret a mano) evita el error "401: invalid_client", que casi
   siempre es un error de transcripción.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/tasks.readonly"]
ARCHIVO_CREDENCIALES = "client_secret.json"

if __name__ == "__main__":
    if not os.path.exists(ARCHIVO_CREDENCIALES):
        print(f"\nERROR: no encuentro '{ARCHIVO_CREDENCIALES}' en esta carpeta.")
        print("Descárgalo desde Google Cloud Console → APIs y servicios → "
              "Credenciales → clic en el ícono de descarga junto a tu ID de "
              "cliente de OAuth → guárdalo aquí con ese nombre exacto.\n")
        raise SystemExit(1)

    flow = InstalledAppFlow.from_client_secrets_file(ARCHIVO_CREDENCIALES, SCOPES)

    # Verificación: muestra qué client_id se está usando, para confirmar
    # que coincide con el que ves en Google Cloud Console.
    import json
    with open(ARCHIVO_CREDENCIALES) as f:
        datos_verif = json.load(f)
        info_verif = datos_verif.get("installed") or datos_verif.get("web")
    print(f"\nUsando client_id: {info_verif['client_id']}")
    print("Verifica que coincida EXACTO con el que ves en Google Cloud Console.\n")
    input("Presiona Enter para continuar y abrir el navegador...")

    creds = flow.run_local_server(port=0)

    # Leer client_id y client_secret del propio JSON, para que coincidan
    # siempre con lo que se usó en la autorización.
    import json
    with open(ARCHIVO_CREDENCIALES) as f:
        datos = json.load(f)
    info = datos.get("installed") or datos.get("web")

    print("\n" + "=" * 60)
    print("¡Listo! Copia estos 3 valores a secrets.toml (sección [google_oauth]):")
    print("=" * 60)
    print(f'client_id     = "{info["client_id"]}"')
    print(f'client_secret = "{info["client_secret"]}"')
    print(f'refresh_token = "{creds.refresh_token}"')
    print("=" * 60)
    print("El refresh_token no caduca mientras no revoques el acceso, "
          "así que este paso NO hay que repetirlo.")
