import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

const SENDER_EMAIL = "bot_tool@sart-full.pt"
const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY')

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { email, verification_code, username, server_name } = await req.json()

    const emailHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verificação de Conta</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f7; font-family: 'Segoe UI', Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f7; padding: 40px 0;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
          <tr>
            <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
              <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">Tool Bot</h1>
              <p style="color: rgba(255,255,255,0.85); margin: 10px 0 0 0; font-size: 16px;">Verificação de Conta</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px 30px;">
              <h2 style="color: #1a1a2e; margin: 0 0 20px 0; font-size: 22px; font-weight: 600;">Olá, ${username}! 👋</h2>
              <p style="color: #4a4a6a; font-size: 16px; line-height: 1.6; margin: 0 0 25px 0;">
                Obrigado por registrar o servidor <strong style="color: #667eea;">${server_name}</strong> no nosso bot.
              </p>
              <p style="color: #4a4a6a; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                Use o código abaixo para verificar sua conta e desbloquear todos os recursos:
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); border-radius: 12px; padding: 25px;">
                <tr>
                  <td align="center">
                    <p style="font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #667eea; margin: 0; font-family: monospace;">${verification_code}</p>
                  </td>
                </tr>
              </table>
              <p style="color: #8888aa; font-size: 14px; margin: 25px 0 0 0; text-align: center;">
                Este código expira em 24 horas. Se você não solicitou, ignore este e-mail.
              </p>
            </td>
          </tr>
          <tr>
            <td style="background-color: #f8f9fa; padding: 25px 30px; text-align: center; border-top: 1px solid #eeeeee;">
              <p style="color: #8888aa; font-size: 13px; margin: 0;">© 2026 Tool Bot. Todos os direitos reservados.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`

    const resendResponse = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${RESEND_API_KEY}`,
      },
      body: JSON.stringify({
        from: `Tool Bot <${SENDER_EMAIL}>`,
        to: [email],
        subject: `[${server_name}] Código de Verificação da Sua Conta`,
        html: emailHtml,
      }),
    })

    const data = await resendResponse.json()
    if (!resendResponse.ok) {
        console.error('Erro retornado pela API do Resend:', data);
        throw new Error('O serviço de e-mail retornou um erro.');
    }

    return new Response(JSON.stringify({ message: "E-mail de verificação enviado!" }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 500,
    })
  }
})
