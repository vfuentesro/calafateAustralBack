import transbank.webpay.webpay_plus.transaction as webpay_plus
from django.conf import settings
from .models import Venta
from django.core.mail import send_mail
from django.template.loader import render_to_string

class TransbankIntegration:
    def __init__(self):
        self.commerce_code = getattr(settings, 'WEBPAY_PLUS_COMMERCE_CODE', '597055555532')  # Código de pruebas
        self.api_key = getattr(settings, 'WEBPAY_PLUS_API_KEY', '597055555532')  # API Key de pruebas
        self.environment = getattr(settings, 'WEBPAY_PLUS_ENVIRONMENT', 'TEST')
        webpay_plus.Transaction.commerce_code = self.commerce_code
        webpay_plus.Transaction.api_key = self.api_key
        webpay_plus.Transaction.environment = self.environment

    def create_transaction(self, venta, return_url):
        # Crea una transacción Webpay Plus
        buy_order = f"VENTA_{venta.id_venta}"
        session_id = str(venta.id_venta)
        amount = int(venta.total_v)
        response = webpay_plus.Transaction.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=amount,
            return_url=return_url
        )
        # Guarda el token en la venta
        venta.transaction_id = response['token']
        venta.save()
        return response

    def commit_transaction(self, token):
        # Confirma la transacción Webpay Plus
        result = webpay_plus.Transaction.commit(token)
        # Si el pago fue exitoso, enviar email
        if result['status'] == 'AUTHORIZED':
            venta = Venta.objects.get(transaction_id=token)
            venta.estado_pago = 'pagado'
            venta.fecha_pago = result.get('transaction_date')
            venta.save()
            self._send_payment_confirmation_email(venta)
        elif result['status'] == 'FAILED':
            venta = Venta.objects.get(transaction_id=token)
            venta.estado_pago = 'rechazado'
            venta.save()
        return result

    def get_status(self, token):
        # Obtiene el estado de la transacción
        return webpay_plus.Transaction.status(token)

    def _send_payment_confirmation_email(self, venta):
        # Enviar email de confirmación al cliente y admin
        subject = f"Confirmación de pago - Calafate Austral"
        message_html = render_to_string('Tienda/emails/confirmacion_pago.html', {
            'venta': venta,
        })
        recipient_list = []
        if venta.usuario and venta.usuario.correo_u:
            recipient_list.append(venta.usuario.correo_u)
        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if admin_email:
            recipient_list.append(admin_email)
        if recipient_list:
            send_mail(
                subject,
                '',
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                html_message=message_html,
                fail_silently=False,
            ) 