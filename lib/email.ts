import nodemailer from 'nodemailer'

export async function enviarCodigoVerificacion(email: string, codigo: string): Promise<boolean> {
  const { SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM } = process.env

  if (!SMTP_HOST || !SMTP_USER || !SMTP_PASS) {
    console.log('==================================================')
    console.log(`[EMAIL DEV MODE] Para: ${email}`)
    console.log(`Código de verificación: ${codigo}`)
    console.log('==================================================')
    return true
  }

  try {
    const transporter = nodemailer.createTransport({
      host: SMTP_HOST,
      port: Number(SMTP_PORT ?? 587),
      secure: Number(SMTP_PORT ?? 587) === 465,
      auth: { user: SMTP_USER, pass: SMTP_PASS },
    })

    await transporter.sendMail({
      from: SMTP_FROM ?? 'noreply@negociosglobales.digital',
      to: email,
      subject: 'Tu código de acceso a ACA',
      html: `
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
          <h2 style="font-size:1.4rem;margin-bottom:8px">Tu código de acceso</h2>
          <p style="color:#666;margin-bottom:24px">Ingresa este código en ACA para continuar:</p>
          <div style="font-size:2rem;font-weight:700;letter-spacing:0.3em;text-align:center;
                      padding:20px;background:#f4f4f5;border-radius:12px;margin-bottom:24px">
            ${codigo}
          </div>
          <p style="color:#999;font-size:0.8rem">Válido por 15 minutos. Si no solicitaste esto, ignora este correo.</p>
        </div>
      `,
    })
    return true
  } catch (err) {
    console.error('[EMAIL ERROR]', err)
    return false
  }
}
