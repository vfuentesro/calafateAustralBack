import requests
import json
import hashlib
import hmac
import base64
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from django.db import transaction
from .models import Venta, Detalleventa
import time

class GetnetIntegration:
    """Clase para manejar la integración con Getnet Web Checkout"""
    
    _access_token = None
    _token_expiry = 0

    def __init__(self):
        # Configuración de Getnet - Reemplazar con tus credenciales reales
        self.merchant_id = getattr(settings, 'GETNET_MERCHANT_ID', 'your_merchant_id')
        self.terminal_id = getattr(settings, 'GETNET_TERMINAL_ID', 'your_terminal_id')
        self.secret_key = getattr(settings, 'GETNET_SECRET_KEY', 'your_secret_key')
        self.api_url = getattr(settings, 'GETNET_API_URL', 'https://api.getnet.cl')
        self.webhook_secret = getattr(settings, 'GETNET_WEBHOOK_SECRET', 'your_webhook_secret')
        # URLs de Getnet
        self.checkout_url = f"{self.api_url}/v1/checkout"
        self.transaction_url = f"{self.api_url}/v1/transactions"
        self.auth_url = getattr(settings, 'GETNET_AUTH_URL', 'https://api.getnet.cl/v1/auth')
        self.client_id = getattr(settings, 'GETNET_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'GETNET_CLIENT_SECRET', '')
    
    def create_checkout_session(self, venta, return_url, cancel_url):
        """
        Crea una sesión de checkout con Getnet
        """
        # Obtener detalles de la venta
        detalles = Detalleventa.objects.filter(id_venta=venta)
        
        # Preparar items para Getnet
        items = []
        for detalle in detalles:
            items.append({
                "name": detalle.id_producto.nombre_p,
                "quantity": detalle.cantidad_dv,
                "unit_price": int(detalle.precio_unitario_dv * 100),  # Getnet requiere centavos
                "sku": str(detalle.id_producto.id_producto)
            })
        
        # Crear payload para Getnet
        payload = {
            "merchant_id": self.merchant_id,
            "terminal_id": self.terminal_id,
            "amount": int(venta.total_v * 100),  # Convertir a centavos
            "currency": "CLP",
            "order_id": f"VENTA_{venta.id_venta}",
            "description": f"Compra en Calafate Austral - Venta #{venta.id_venta}",
            "items": items,
            "customer": {
                "name": f"{venta.usuario.nombre_u} {venta.usuario.apellido_u}",
                "email": venta.usuario.correo_u,
                "phone": venta.usuario.numero_telefono_u,
                "document": venta.usuario.rut_usuario
            },
            "return_url": return_url,
            "cancel_url": cancel_url,
            "webhook_url": f"{settings.BASE_URL}/getnet/webhook/",
            "expires_at": (datetime.now().timestamp() + 3600),  # Expira en 1 hora
            "metadata": {
                "venta_id": venta.id_venta,
                "user_rut": venta.usuario.rut_usuario
            }
        }
        
        # Generar firma
        signature = self._generate_signature(payload)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._get_access_token()}',
            'X-Signature': signature
        }
        
        try:
            response = requests.post(
                self.checkout_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al crear sesión de checkout: {str(e)}")
    
    def verify_webhook(self, payload, signature):
        """
        Verifica la autenticidad del webhook de Getnet
        """
        expected_signature = self._generate_signature(payload)
        return hmac.compare_digest(signature, expected_signature)
    
    def process_webhook(self, payload):
        """
        Procesa el webhook de Getnet y actualiza el estado de la venta.
        Si el pago es aprobado, descuenta el stock de los productos.
        """
        try:
            # Extraer información del webhook
            order_id = payload.get('order_id')
            status = payload.get('status')
            transaction_id = payload.get('transaction_id')
            
            # Extraer ID de venta del order_id
            if not order_id or not order_id.startswith('VENTA_'):
                raise Exception("Formato de order_id inválido")
            
            venta_id = int(order_id.split('_')[1])
            
            with transaction.atomic():
                venta = Venta.objects.select_for_update().get(id_venta=venta_id)
                
                # Prevenir doble procesamiento
                if venta.estado_pago == 'pagado':
                    # Ya fue procesado, no hacer nada.
                    return True

                # Actualizar estado según el status
                if status == 'approved':
                    venta.estado_pago = 'pagado'
                    venta.transaction_id = transaction_id
                    venta.fecha_pago = datetime.now()
                    venta.save()
                    
                    # Descontar stock
                    detalles = Detalleventa.objects.filter(id_venta=venta)
                    for detalle in detalles:
                        producto = detalle.id_producto
                        # Usar F() para evitar race conditions
                        if producto.stock_p >= detalle.cantidad_dv:
                            producto.stock_p -= detalle.cantidad_dv
                            producto.save(update_fields=['stock_p'])
                        else:
                            # Esto no debería pasar si la validación en la compra es correcta,
                            # pero es una salvaguarda importante.
                            # Aquí se podría registrar un error crítico.
                            raise Exception(f"Stock insuficiente para producto {producto.id_producto} en venta {venta.id_venta}")
                    
                    # Aquí podrías enviar email de confirmación
                    self._send_payment_confirmation_email(venta)
                    
                elif status in ['declined', 'cancelled']:
                    venta.estado_pago = 'rechazado'
                    venta.save()
                    
                elif status == 'pending':
                    # Si ya estaba pendiente, no hacemos nada.
                    # Si venía de otro estado, lo actualizamos.
                    if venta.estado_pago != 'pendiente':
                        venta.estado_pago = 'pendiente'
                        venta.save()
            
            return True
            
        except Venta.DoesNotExist:
            # La venta no existe, puede ser un webhook de prueba o un error. Ignorar.
            return True
        except Exception as e:
            # Idealmente, loggear el error aquí
            raise Exception(f"Error procesando webhook: {str(e)}")
    
    def get_transaction_status(self, transaction_id):
        """
        Consulta el estado de una transacción
        """
        headers = {
            'Authorization': f'Bearer {self._get_access_token()}'
        }
        
        try:
            response = requests.get(
                f"{self.transaction_url}/{transaction_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error consultando transacción: {str(e)}")
    
    def _generate_signature(self, payload):
        """
        Genera la firma HMAC para autenticar las peticiones
        """
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_access_token(self):
        # Si el token es válido, lo usamos
        if GetnetIntegration._access_token and GetnetIntegration._token_expiry > time.time() + 60:
            return GetnetIntegration._access_token

        # Si no, pedimos uno nuevo
        payload = {
            "merchant_id": self.merchant_id,
            "user": getattr(settings, 'GETNET_LOGIN', ''),
            "password": self.secret_key
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.auth_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        GetnetIntegration._access_token = data['access_token']
        GetnetIntegration._token_expiry = time.time() + int(data.get('expires_in', 3600))
        return GetnetIntegration._access_token
    
    def _send_payment_confirmation_email(self, venta):
        """
        Envía email de confirmación de pago
        """
        # Implementar envío de email de confirmación
        pass 