import os, ssl, smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, make_msgid
from flask import Flask, request, redirect, Response, send_file, jsonify
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__, static_folder="assets", template_folder=".")

@app.get("/")
def home():
    return send_file("index.html")


@app.post("/contact")
def contact():
    # Soporta form-url-encoded (formulario) y JSON (si alguna vez lo usas)
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
        return jsonify({"ok": False, "error": str(e)}), 500


def send_email(name: str, email: str, message: str):
    host    = os.getenv("SMTP_HOST")
    port    = int(os.getenv("SMTP_PORT", "587"))
    from_addr    = os.getenv("SMTP_USER")
    pwd     = os.getenv("SMTP_PASS")
    to_addr = os.getenv("SMTP_TO")                   # dónde recibes contactos
    use_tls = os.getenv("SMTP_TLS", "1") == "1"
    send_ack = os.getenv("SEND_ACK", "1") == "1"     # desactiva con SEND_ACK=0

    if not to_addr:
        raise RuntimeError("Falta SMTP_TO en .env")

    # -------- 1) Correo a administración (tú) --------
    admin_subject = "Nuevo contacto – TastePro"
    admin_body = (
        f"Nombre: {name}\n"
        f"Correo: {email}\n\n"
        f"Mensaje:\n{message}\n"
    )
    admin_msg = MIMEText(admin_body, "plain", "utf-8")
    admin_msg["Subject"]   = str(Header(admin_subject, "utf-8"))
    admin_msg["From"]      = formataddr(("TastePro", from_addr))
    admin_msg["To"]        = to_addr
    admin_msg["Reply-To"]  = email
    admin_msg["Message-ID"]= make_msgid()

    # -------- 2) Acuse de recibo al usuario --------
    ack_subject = "Hemos recibido tu mensaje – TastePro"
    ack_body = (
        f"Hola {name},\n\n"
        "Gracias por contactarnos. Hemos recibido tu mensaje y nuestro equipo lo revisará a la brevedad.\n\n"
        "Resumen de tu envío:\n"
        f"- Correo: {email}\n"
        "----------------------------------------\n"
        f"{message}\n"
        "----------------------------------------\n\n"
        "Saludos,\n"
        "Equipo TastePro"
    )
    ack_msg = MIMEText(ack_body, "plain", "utf-8")
    ack_msg["Subject"]    = str(Header(ack_subject, "utf-8"))
    ack_msg["From"]       = formataddr(("TastePro", from_addr))
    ack_msg["To"]         = email
    ack_msg["Reply-To"]   = to_addr
    ack_msg["Message-ID"] = make_msgid()

    # DRY-RUN si falta host (útil en desarrollo)
    if not host:
        print("=== DRY-RUN EMAIL (ADMIN) ===")
        print(admin_msg.as_string())
        print("=== DRY-RUN EMAIL (ACK) ===")
        if send_ack:
            print(ack_msg.as_string())
        else:
            print("(ACK desactivado por SEND_ACK=0)")
        print("=============================")
        return

    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=15) as s:
        if use_tls:
            s.starttls(context=ctx)
        if user and pwd:
            s.login(user, pwd)

        # envía a administración
        s.send_message(admin_msg, from_addr=from_addr, to_addrs=[to_addr])

        # envía acuse al usuario (si está activo)
        if send_ack:
            s.send_message(ack_msg, from_addr=from_addr, to_addrs=[email])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)

