import json
import requests
from os import environ as env
from urllib.parse import quote_plus, urlencode
 
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
 
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)
 
app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")
 
oauth = OAuth(app)
 
oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)
 
 
# Controllers API
@app.route("/")
def home():
    return render_template(
        "home.html",
        session=session.get("user"),
        pretty=json.dumps(session.get("user"), indent=4),
    )
 
 
@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")
 
 
@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )
 
 
@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://"
        + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )
 
 
# Ruta para editar el perfil
@app.route("/edit-profile", methods=["POST"])
def edit_profile():
    if "user" not in session:
        return redirect("/login")
 
    # Obtener datos del formulario
    tipo_documento = request.form.get("tipoDocumento")
    numero_documento = request.form.get("numeroDocumento")
    direccion = request.form.get("direccion")
    telefono = request.form.get("telefono")
 
    # Obtener token de Management API
    domain = env.get("AUTH0_DOMAIN")
    client_id = env.get("AUTH0_CLIENT_ID")
    client_secret = env.get("AUTH0_CLIENT_SECRET")
 
    token_url = f"https://{domain}/oauth/token"
    token_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": f"https://{domain}/api/v2/",
        "grant_type": "client_credentials"
    }
    token_response = requests.post(token_url, json=token_payload)
    mgmt_token = token_response.json().get("access_token")
 
    if not mgmt_token:
        return "Error obteniendo el token de Management API", 500
 
    # Construir el payload de la actualización del perfil
    payload = json.dumps({
        "user_metadata": {
            "tipoDocumento": tipo_documento,
            "numeroDocumento": numero_documento,
            "direccion": direccion,
            "telefono": telefono
        }
    })
 
    # Llamar a la API de Management para actualizar el perfil
    user_id = session["user"]["userinfo"]["sub"]
    headers = {
        'Authorization': f"Bearer {mgmt_token}",
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    url = f"https://{domain}/api/v2/users/{user_id}"
 
    response = requests.patch(url, headers=headers, data=payload)
 
    if response.status_code == 200:
        # Actualizar la sesión con los nuevos datos
        session["user"]["userinfo"]["user_metadata"] = json.loads(payload)["user_metadata"]
        return redirect(url_for("home"))
    else:
        return f"Error actualizando el perfil: {response.json()}", 500
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=env.get("PORT", 3000))