"""Envío de correos transaccionales para ACA."""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import APP_URL, SMTP_FROM, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER

_DEV_MODE = not (SMTP_HOST and SMTP_USER)


def enviar_codigo_verificacion(email: str, codigo: str) -> bool:
    """Envía el código de verificación al correo. Devuelve True si fue exitoso."""
    subject = f"Tu código de acceso ACA: {codigo}"

    text_body = (
        f"Hola,\n\n"
        f"Tu código de verificación para ACA es:\n\n"
        f"  {codigo}\n\n"
        f"Este código expira en 15 minutos.\n\n"
        f"Si no solicitaste esto, ignora este correo.\n\n"
        f"— Equipo ACA"
    )

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:'Inter',system-ui,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;border:1px solid rgba(0,0,0,0.08);overflow:hidden">
        <!-- header -->
        <tr>
          <td style="background:#000;padding:24px 32px;text-align:center">
            <span style="color:#fff;font-size:18px;font-weight:700;letter-spacing:-.03em">ACA</span>
          </td>
        </tr>
        <!-- body -->
        <tr>
          <td style="padding:36px 32px">
            <p style="margin:0 0 12px;font-size:15px;color:#111;font-weight:600">Tu código de verificación</p>
            <p style="margin:0 0 28px;font-size:14px;color:#666;line-height:1.6">
              Usa este código para acceder a ACA. Expira en <strong>15 minutos</strong>.
            </p>
            <div style="background:#f4f4f5;border-radius:10px;padding:20px;text-align:center;margin-bottom:28px">
              <span style="font-size:32px;font-weight:700;letter-spacing:.2em;color:#000;
                           font-family:'JetBrains Mono',monospace">{codigo}</span>
            </div>
            <p style="margin:0;font-size:12px;color:#aaa;line-height:1.5">
              Si no solicitaste este código, puedes ignorar este correo.
            </p>
          </td>
        </tr>
        <!-- footer -->
        <tr>
          <td style="padding:16px 32px;border-top:1px solid #f0f0f0">
            <p style="margin:0;font-size:12px;color:#aaa;text-align:center">
              ACA — Clasificación Arancelaria · <a href="{APP_URL}" style="color:#555">{APP_URL}</a>
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    if _DEV_MODE:
        print(f"\n{'='*50}")
        print(f"[EMAIL DEV MODE] Para: {email}")
        print(f"Código de verificación: {codigo}")
        print(f"{'='*50}\n")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, email, msg.as_string())
        return True
    except Exception as exc:
        print(f"[EMAIL ERROR] {exc}")
        return False
