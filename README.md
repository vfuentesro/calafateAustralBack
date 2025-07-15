# Calafate Austral - Back-end

Este es el back-end de la tienda Calafate Austral, desarrollado en Django. Expone una API REST para la gestión de productos, usuarios, ventas, ofertas y pagos, incluyendo integración con Getnet Chile.

## Características principales
- Django 5 + Django REST Framework
- Autenticación JWT y sesiones
- Gestión de productos, usuarios, ventas, ofertas y contactos
- Integración con Getnet para pagos en línea
- Soporte para métodos de envío (Chilexpress, CorreosChile)
- Panel de administración y endpoints para dashboard

## Instalación y configuración

1. **Clona el repositorio y entra al directorio `back-end`:**
   ```bash
   git clone <repo-url>
   cd back-end
   ```
2. **Crea y activa un entorno virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```
3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configura las variables de entorno:**
   - Crea un archivo `.env` en la raíz con tus credenciales y configuración (ver ejemplo en `GETNET_SETUP.md`).
   - Variables importantes: `SECRET_KEY`, `DEBUG`, credenciales de Getnet, configuración de base de datos, etc.

5. **Aplica las migraciones:**
   ```bash
   python manage.py migrate
   ```
6. **Crea un superusuario (opcional, para admin):**
   ```bash
   python manage.py createsuperuser
   ```

## Ejecución

- **Desarrollo:**
  ```bash
  python manage.py runserver
  ```
- **Producción (Docker):**
  ```bash
  docker build -t calafate-backend .
  docker run -p 8080:8080 calafate-backend
  ```
  O usando el comando de la imagen:
  ```bash
  python manage.py collectstatic --noinput && python manage.py migrate && gunicorn Backedn_Calafate_Austral.wsgi:application --bind 0.0.0.0:8080
  ```

## Endpoints principales
- `/api/usuarios/` - Gestión de usuarios
- `/api/productos/` - Gestión de productos
- `/api/ventas/` - Gestión de ventas
- `/api/ofertas/` - Gestión de ofertas
- `/api/checkout/` - Proceso de compra
- `/api/shipping/quote/` - Cotización de envío
- `/api/token/` y `/api/token/refresh/` - Autenticación JWT
- `/getnet/` - Endpoints de integración con Getnet

## Dependencias principales
- Django, djangorestframework, djangorestframework-simplejwt
- Pillow, requests, mysqlclient, cryptography, zeep
- django-environ, django-crispy-forms, django-cors-headers, gunicorn, argon2-cffi

## Integración con Getnet
- Sigue la guía en `GETNET_SETUP.md` para configurar credenciales y webhooks.
- Prueba la integración con el script `test_getnet_integration.py`.

## Pruebas
- Ejecuta los tests con:
  ```bash
  python test_getnet_integration.py
  ```

## Notas
- El back-end requiere una base de datos MySQL configurada.
- Para producción, configura correctamente las variables de entorno y los orígenes permitidos (CORS/CSRF).
- El panel de administración está disponible en `/admin/`.

---

Desarrollado por Calafate Austral. 