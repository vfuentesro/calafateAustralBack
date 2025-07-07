import requests
from .models import Detalleventa
from django.conf import settings
from zeep import Client
from zeep.exceptions import Fault
import logging

logger = logging.getLogger(__name__)

class ChilexpressAPI:
    """
    Clase para manejar la integración con la API REST de Chilexpress.
    """
    def __init__(self):
        self.api_key = settings.CHILEXPRESS_API_KEY
        self.base_url = settings.CHILEXPRESS_API_URL
        self.headers = {
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': self.api_key
        }

    def seguimiento_envio(self, numero_seguimiento):
        url = f"{self.base_url}shipments/{numero_seguimiento}/tracking"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None

    def crear_envio(self, datos_envio):
        # Completa aquí con los campos requeridos por la API real
        url = f"{self.base_url}shipments"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=datos_envio)
        if response.status_code == 200:
            return response.json()
        return None

    def cotizar_envio(self, origen, destino, alto, ancho, largo, peso, producto_servicio='3'):
        """
        Cotiza un envío utilizando la API de Chilexpress.

        :param origen: Código de comuna de origen.
        :param destino: Código de comuna de destino.
        :param alto: Alto del paquete en cm.
        :param ancho: Ancho del paquete en cm.
        :param largo: Largo del paquete en cm.
        :param peso: Peso del paquete en kg.
        :param producto_servicio: Código del tipo de servicio (ej. '3' para día hábil siguiente).
        :return: Diccionario con la respuesta de la API o None si hay error.
        """
        url = f"{self.base_url}/v1.0/cotizador"
        payload = {
            "origen": str(origen),
            "destino": str(destino),
            "producto": str(producto_servicio),
            "alto": str(alto),
            "ancho": str(ancho),
            "largo": str(largo),
            "peso": str(peso)
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()  # Lanza un error para respuestas 4xx/5xx
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"Error HTTP al cotizar en Chilexpress: {http_err} - {response.text}")
            return None
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Error de conexión al cotizar en Chilexpress: {req_err}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al cotizar en Chilexpress: {e}")
            return None

class CorreosChileAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.correos.cl/v1/"

    def seguimiento_envio(self, numero_seguimiento):
        url = f"{self.base_url}seguimiento/{numero_seguimiento}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None

    def crear_envio(self, datos_envio):
        # Completa aquí con los campos requeridos por la API real
        url = f"{self.base_url}envios"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=datos_envio)
        if response.status_code == 200:
            return response.json()
        return None

# Automatización para actualizar estado de Detalleventa
def actualizar_estado_envio(detalle_id, empresa='chilexpress'):
    detalle = Detalleventa.objects.get(pk=detalle_id)
    if not detalle.numero_seguimiento:
        return "No hay número de seguimiento"

    if empresa == 'chilexpress':
        api = ChilexpressAPI()
        resultado = api.seguimiento_envio(detalle.numero_seguimiento)
        if resultado:
            # Este mapeo depende de la respuesta real de la API
            estado_api = resultado.get('estado', '').lower() if isinstance(resultado, dict) else ''
            if 'entregado' in estado_api:
                detalle.estado = 'entregado'
            elif 'enviado' in estado_api or 'transito' in estado_api:
                detalle.estado = 'envio'
            elif 'bodega' in estado_api or 'preparando' in estado_api:
                detalle.estado = 'bodega'
            detalle.save()
            return f"Estado actualizado a {detalle.get_estado_display()}"
        return "No se pudo obtener el estado"
    elif empresa == 'correoschile':
        api = CorreosChileAPI(api_key='TU_API_KEY')
        resultado = api.seguimiento_envio(detalle.numero_seguimiento)
        # Mapeo similar según la respuesta de Correos Chile
        return "Integración Correos Chile pendiente"
    else:
        return "Empresa no soportada"

def enviar_a_chilexpress(direccion, datos_envio):
    api = ChilexpressAPI()
    return api.crear_envio(datos_envio)

def enviar_a_correos_chile(direccion, datos_envio):
    api = CorreosChileAPI(api_key='TU_API_KEY')
    return api.crear_envio(datos_envio)

# Ejemplo de uso:
# chilexpress = ChilexpressAPI()
# resultado = chilexpress.seguimiento_envio("NUMERO_SEGUIMIENTO")
# print(resultado)

class CorreosChileIntegration:
    """
    Clase para manejar la integración con la API SOAP de Correos de Chile.
    """
    def __init__(self):
        self.wsdl_url = settings.CORREOS_CHILE_API_URL
        self.user = settings.CORREOS_CHILE_USER
        self.password = settings.CORREOS_CHILE_PASSWORD
        try:
            self.client = Client(self.wsdl_url)
        except Exception as e:
            logger.error(f"Error al inicializar el cliente SOAP de Correos de Chile: {e}")
            self.client = None

    def cotizar_envio(self, comuna_origen, comuna_destino, kilos, volumen):
        """
        Consulta la API de Correos de Chile para obtener las tarifas de envío.

        :param comuna_origen: Código de la comuna de origen.
        :param comuna_destino: Código de la comuna de destino.
        :param kilos: Peso total del paquete en kilos (string).
        :param volumen: Volumen total del paquete (ej: '0.1' para 10x10x10cm).
        :return: Una lista de servicios con sus tarifas, o None si hay un error.
        """
        if not self.client:
            return None

        try:
            # El objeto 'cobertura' debe coincidir con la estructura definida en el WSDL de Correos.
            # Basado en la documentación de su API.
            cobertura = {
                'ComunaRemitente': comuna_origen,
                'ComunaDestino': comuna_destino,
                'Kilos': str(kilos),
                'Volumen': str(volumen),
                'NumeroTotalPieza': '1',
                'PaisRemitente': '056', # Código para Chile
                'PaisDestinatario': '056',
                # Otros campos opcionales pueden dejarse en blanco o con valores por defecto.
                'CodigoPostalRemitente': '',
                'CodigoPostalDestinatario': '',
                'ImporteValorAsegurado': '0',
                'ImporteReembolso': '0',
                'TipoPortes': 'P' # P: Pagado, D: Debidos
            }
            
            # Llamada al método SOAP 'consultaCobertura'
            resultado = self.client.service.consultaCobertura(
                usuario=self.user,
                contrasena=self.password,
                consultaCobertura=cobertura
            )
            
            # El resultado puede venir anidado. Es importante inspeccionar la respuesta.
            if resultado and hasattr(resultado, 'ServicioTO'):
                return resultado.ServicioTO
            return resultado

        except Fault as fault:
            logger.error(f"Error SOAP al cotizar en Correos de Chile: {fault.message}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al cotizar en Correos de Chile: {e}")
            return None 