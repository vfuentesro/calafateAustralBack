# Configuración de Getnet para Calafate Austral

## Descripción
Esta guía te ayudará a configurar la integración con [Getnet Chile](https://www.getnet.cl/developers) para procesar pagos en tu tienda online.

## Requisitos Previos

1. **Cuenta de Comercio Getnet**: Necesitas registrarte como comercio en Getnet Chile
2. **Credenciales de API**: Obtener las credenciales de desarrollo y producción
3. **Dominio HTTPS**: Para webhooks en producción (requerido por Getnet)

## Paso 1: Registro en Getnet

1. Visita [Getnet Chile](https://www.getnet.cl/developers)
2. Regístrate como comercio
3. Solicita acceso a la API de Web Checkout
4. Obtén tus credenciales de desarrollo

## Paso 2: Configuración de Credenciales

Edita el archivo `Backedn_Calafate_Austral/settings.py` y reemplaza las siguientes variables:

```python
# Configuración de Getnet
GETNET_MERCHANT_ID = 'tu_merchant_id_real'
GETNET_TERMINAL_ID = 'tu_terminal_id_real'
GETNET_SECRET_KEY = 'tu_secret_key_real'
GETNET_ACCESS_TOKEN = 'tu_access_token_real'
GETNET_WEBHOOK_SECRET = 'tu_webhook_secret_real'
GETNET_API_URL = 'https://api.getnet.cl'  # Para producción
# GETNET_API_URL = 'https://api-sandbox.getnet.cl'  # Para desarrollo
```

## Paso 3: Configuración de Webhooks

### Desarrollo Local
Para desarrollo local, puedes usar herramientas como ngrok para exponer tu servidor local:

1. Instala ngrok: `npm install -g ngrok`
2. Ejecuta: `ngrok http 8000`
3. Usa la URL HTTPS generada para configurar el webhook en Getnet

### Producción
En producción, configura el webhook en el panel de Getnet con:
- URL: `https://tudominio.com/getnet/webhook/`
- Método: POST
- Eventos: payment.success, payment.failed, payment.pending

## Paso 4: Configuración del Entorno

### Variables de Entorno (Recomendado)
Crea un archivo `.env` en la raíz del proyecto:

```env
GETNET_MERCHANT_ID=tu_merchant_id
GETNET_TERMINAL_ID=tu_terminal_id
GETNET_SECRET_KEY=tu_secret_key
GETNET_ACCESS_TOKEN=tu_access_token
GETNET_WEBHOOK_SECRET=tu_webhook_secret
BASE_URL=https://tudominio.com
```

### Instalar python-dotenv
```bash
pip install python-dotenv
```

### Actualizar settings.py
```python
from dotenv import load_dotenv
load_dotenv()

GETNET_MERCHANT_ID = os.getenv('GETNET_MERCHANT_ID')
GETNET_TERMINAL_ID = os.getenv('GETNET_TERMINAL_ID')
GETNET_SECRET_KEY = os.getenv('GETNET_SECRET_KEY')
GETNET_ACCESS_TOKEN = os.getenv('GETNET_ACCESS_TOKEN')
GETNET_WEBHOOK_SECRET = os.getenv('GETNET_WEBHOOK_SECRET')
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')
```

## Paso 5: Pruebas

### 1. Probar Checkout
1. Agrega productos al carrito
2. Inicia sesión
3. Haz clic en "Pagar con Getnet"
4. Completa el proceso de pago en el sandbox de Getnet

### 2. Probar Webhooks
1. Usa las herramientas de prueba de Getnet
2. Verifica que los webhooks lleguen correctamente
3. Revisa los logs en `logs/django.log`

### 3. Verificar Estados
- Los pagos exitosos deben cambiar a estado "pagado"
- Los pagos rechazados deben cambiar a estado "rechazado"
- Los pagos cancelados deben cambiar a estado "cancelado"

## Paso 6: Monitoreo y Logs

### Logs de la Aplicación
Los logs se guardan en `logs/django.log` y incluyen:
- Creación de sesiones de checkout
- Recepción de webhooks
- Errores de procesamiento
- Confirmaciones de pago

### Monitoreo de Transacciones
Puedes consultar el estado de una transacción usando:
```
GET /getnet/payment-status/{venta_id}/
```

## Paso 7: Producción

### Checklist de Producción
- [ ] Credenciales de producción configuradas
- [ ] Webhook configurado con URL de producción
- [ ] SSL/HTTPS habilitado
- [ ] Logs configurados correctamente
- [ ] Pruebas completadas en sandbox
- [ ] Monitoreo de transacciones activo

### Configuración de Seguridad
1. **Nunca** commits credenciales reales al repositorio
2. Usa variables de entorno en producción
3. Configura firewalls para proteger los webhooks
4. Monitorea logs regularmente

## Solución de Problemas

### Error: "No se pudo obtener la URL de checkout"
- Verifica que las credenciales sean correctas
- Asegúrate de que la API de Getnet esté disponible
- Revisa los logs para más detalles

### Error: "Webhook con firma inválida"
- Verifica que el webhook secret sea correcto
- Asegúrate de que la URL del webhook esté bien configurada
- Revisa que el método HTTP sea POST

### Error: "Venta no encontrada"
- Verifica que la venta exista en la base de datos
- Asegúrate de que el order_id esté bien formateado
- Revisa los logs de creación de ventas

## Recursos Adicionales

- [Documentación de Getnet Chile](https://www.getnet.cl/developers)
- [API Reference de Getnet](https://api.getnet.cl/docs)
- [Centro de Ayuda Getnet](https://www.getnet.cl/soporte)

## Soporte

Si tienes problemas con la integración:
1. Revisa los logs en `logs/django.log`
2. Verifica la configuración de credenciales
3. Contacta al soporte de Getnet Chile
4. Revisa la documentación oficial de Getnet

---

**Nota**: Esta integración está diseñada para el mercado chileno. Para otros países, consulta la documentación específica de Getnet en tu región. 