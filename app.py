import os, ssl, smtplib, json
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, make_msgid
from flask import Flask, request, redirect, Response, send_file, jsonify
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="assets", template_folder=".")

@app.get("/")
def home():
    return send_file("index.html")

@app.post("/contact")
def contact():
    # Soporta form-url-encoded (formulario) y JSON
    if request.is_json:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        message = (data.get("message") or "").strip()
    else:
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        message = (request.form.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "Faltan campos"}), 400

    try:
        send_email(name, email, message)
        return jsonify({"ok": True})
    except Exception as e:
        # Devuelve el mensaje extendido que construimos en send_email
        app.logger.exception("Fallo al enviar correo")
        app.logger.exception(f"El error completo fue: {e}")
        return jsonify({"ok": False, "error": "Lo sentimos hubo un error al enviar el correo."}), 500  # 👈 mensaje corto visible en la web

    

def send_email(name: str, email: str, message: str):
    """
    Envía 2 correos vía SendGrid:
      1) A la administración (TO) con Reply-To del usuario.
      2) Acuse de recibo al usuario (si SEND_ACK=1).

    Variables de entorno usadas:
      - SENDGRID_API_KEY_TASTEPRO
      - USER (remitente, ej. no-reply@tudominio)
      - NAME (nombre del remitente, ej. TastePro)
      - TO   (destino administración)
      - SEND_ACK (1/0)
    """
    api_key   = os.getenv("SENDGRID_API_KEY_TASTEPRO")
    from_addr = os.getenv("EMAIL_USER")
    from_name = os.getenv("EMAIL_NAME")
    to_addr   = os.getenv("EMAIL_TO")
    send_ack  = os.getenv("SEND_ACK", "1") == "1"

    if not api_key:
        raise RuntimeError("Config: falta SENDGRID_API_KEY_TASTEPRO")
    if not from_addr:
        raise RuntimeError("Config: falta USER (correo remitente)")
    if not to_addr:
        raise RuntimeError("Config: falta TO (correo de administración)")

    # -------- 1) Correo a administración --------
    admin_subject = "Nuevo mensaje recibido desde TastePro"
    admin_body_txt = (
        f"Nombre: {name}\n"
        f"Correo: {email}\n\n"
        f"Mensaje:\n{message}\n"
        f"TastePro\n"
    )
    admin_msg = Mail(
        from_email=Email(from_addr, from_name),
        to_emails=to_addr,
        subject=admin_subject,
        plain_text_content=admin_body_txt,
    )
    admin_msg.reply_to = Email(email)

    # -------- 2) Acuse de recibo al usuario --------
    ack_subject = "Hemos recibido tu mensaje – TastePro"
    ack_body_txt = (
        f"Hola {name},\n\n"
        "Gracias por contactarnos. Hemos recibido tu mensaje y nuestro equipo "
        "lo revisará a la brevedad.\n\n"
        "Resumen de tu envío:\n"
        f"- Correo: {email}\n"
        "----------------------------------------\n"
        f"{message}\n"
        "----------------------------------------\n\n"
        "Saludos,\n"
        "Equipo TastePro"
    )
    ack_msg = Mail(
        from_email=Email(from_addr, from_name),
        to_emails=email,
        subject=ack_subject,
        plain_text_content=ack_body_txt,
    )
    ack_msg.reply_to = Email(to_addr)

    sg = SendGridAPIClient(api_key)

    # ---- Envío con captura de error VERBOSA ----
    try:
        resp_admin = sg.send(admin_msg)
        print("ADMIN:", resp_admin.status_code)
        if send_ack:
            resp_ack = sg.send(ack_msg)
            print("ACK:", resp_ack.status_code)
    except Exception as e:
        # SendGrid suele exponer .body (JSON) y .status_code/.status, y a veces .headers
        status = getattr(e, "status_code", getattr(e, "status", None))
        body   = getattr(e, "body", None)
        headers = getattr(e, "headers", None)

        # Normaliza el cuerpo a string legible
        if isinstance(body, bytes):
            body_txt = body.decode("utf-8", errors="ignore")
        elif isinstance(body, (dict, list)):
            body_txt = json.dumps(body, ensure_ascii=False)
        elif body is not None:
            body_txt = str(body)
        else:
            body_txt = ""

        # Construye un mensaje claro para propagar hasta /contact
        details = {
            "type": e.__class__.__name__,
            "status": status,
            "body": body_txt.strip() or None,
        }
        # Opcional: adjuntar algunos headers útiles si existen
        if headers:
            try:
                details["x-request-id"] = headers.get("X-Request-Id") or headers.get("X-Message-Id")
            except Exception:
                pass

        raise RuntimeError(f"SendGrid error: {json.dumps(details, ensure_ascii=False)}") from e

if __name__ == "__main__":
    # debug=True para ver trazas en consola
    app.run(host="127.0.0.1", port=8000, debug=True)
