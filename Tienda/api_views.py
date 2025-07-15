import json
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from .models import Producto, Categoria, Venta, Detalleventa, Usuario, Oferta, Contacto, ImagenProducto
from .serializers import (
    ProductoSerializer, CategoriaSerializer, CartSerializer, VentaDashboardSerializer,
    OfertaSerializer, ContactoSerializer, ImagenProductoSerializer, DetalleventaSerializer,
    UsuarioSerializer, VentaSerializer, CustomTokenObtainPairSerializer
)
from .getnet_integration import GetnetIntegration
from .servicios_envio import ChilexpressAPI, CorreosChileIntegration
from .transbank_integration import TransbankIntegration
from django.urls import reverse
from .models import Venta, Detalleventa, Producto
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminUser]

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer
    permission_classes = [IsAdminUser]

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all().order_by('-id_producto')
    serializer_class = ProductoSerializer
    lookup_field = 'id_producto'

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

class CategoriaViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows categories to be viewed.
    """
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAdminUser]

class CheckoutView(APIView):
    def post(self, request, *args, **kwargs):
        cart_serializer = CartSerializer(data=request.data)
        if not cart_serializer.is_valid():
            return Response(cart_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = cart_serializer.validated_data
        cart_items = validated_data['cart']
        
        try:
            with transaction.atomic():
                # Crear la venta
                venta = Venta.objects.create(
                    tipo_comprador='invitado', # O determinar si es usuario logueado
                    total_v=0 # Se calculará a continuación
                )

                total_venta = 0
                for item in cart_items:
                    producto = Producto.objects.get(sku=item['sku'])
                    cantidad = item['quantity']
                    
                    if producto.stock_p < cantidad:
                        raise Exception(f"No hay suficiente stock para {producto.nombre_p}")

                    precio = producto.precio_p
                    subtotal = precio * cantidad
                    total_venta += subtotal
                    
                    Detalleventa.objects.create(
                        id_venta=venta,
                        id_producto=producto,
                        cantidad_v=cantidad,
                        precio_unitario=precio,
                        subtotal=subtotal
                    )
                    
                    # Descontar stock
                    producto.stock_p -= cantidad
                    producto.save()

                venta.total_v = total_venta
                venta.save()

            # Iniciar pago con Getnet
            getnet = GetnetIntegration()
            payment_response = getnet.create_payment(
                amount=int(total_venta),
                currency="CLP",
                order_id=str(venta.id_venta)
            )

            if not payment_response or 'redirectUrl' not in payment_response:
                raise Exception("Error al iniciar el pago con Getnet.")
            
            # Guardar el ID de la sesión de Getnet en la venta
            venta.checkout_session_id = payment_response.get('requestId')
            venta.save()

            response_data = {
                'payment_url': payment_response['redirectUrl'],
                'token': payment_response.get('token') # si aplica
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Producto.DoesNotExist:
            return Response({"error": "Uno o más productos no fueron encontrados."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Error en el checkout: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ShippingQuoteView(APIView):
    def post(self, request, *args, **kwargs):
        cart = request.data.get('cart', [])
        destination_commune_code = request.data.get('destination_commune_code')
        origin_commune_code = request.data.get('origin_commune_code', '9170023') # Default a Las Condes, por ejemplo

        if not cart or not destination_commune_code:
            return Response({'error': 'Se requiere el carrito y la comuna de destino.'}, status=status.HTTP_400_BAD_REQUEST)

        total_weight_kg = 0
        total_volume_m3 = 0
        alto_cm_total = 0
        ancho_cm_total = 0
        largo_cm_total = 0

        for item in cart:
            try:
                producto = Producto.objects.get(sku=item.get('sku'))
                quantity = int(item.get('quantity', 1))
                
                total_weight_kg += (producto.peso_kg or 0) * quantity
                
                volumen_item_m3 = ((producto.alto_cm or 0) * (producto.ancho_cm or 0) * (producto.largo_cm or 0)) / 1_000_000
                total_volume_m3 += volumen_item_m3 * quantity
                
                alto_cm_total += (producto.alto_cm or 0) * quantity
                if (producto.ancho_cm or 0) > ancho_cm_total:
                    ancho_cm_total = (producto.ancho_cm or 0)
                if (producto.largo_cm or 0) > largo_cm_total:
                    largo_cm_total = (producto.largo_cm or 0)

            except Producto.DoesNotExist:
                return Response({'error': f"Producto con SKU {item.get('sku')} no encontrado."}, status=status.HTTP_404_NOT_FOUND)
            except (ValueError, TypeError):
                 return Response({'error': 'Cantidad inválida para un producto.'}, status=status.HTTP_400_BAD_REQUEST)

        if total_weight_kg == 0:
            return Response({'error': 'No se pudo calcular el peso del envío. Revisa los datos de los productos.'}, status=status.HTTP_400_BAD_REQUEST)

        shipping_quotes = []

        # Chilexpress
        chilexpress_api = ChilexpressAPI()
        chilexpress_quote = chilexpress_api.cotizar_envio(
            origen=origin_commune_code,
            destino=destination_commune_code,
            alto=max(1, int(alto_cm_total)),
            ancho=max(1, int(ancho_cm_total)),
            largo=max(1, int(largo_cm_total)),
            peso=max(0.1, total_weight_kg)
        )
        if chilexpress_quote and chilexpress_quote.get('valor_servicio'):
            shipping_quotes.append({
                'carrier': 'Chilexpress',
                'service_name': chilexpress_quote.get('descripcion_servicio', 'Envío Estándar'),
                'price': chilexpress_quote.get('valor_servicio'),
                'delivery_estimate': chilexpress_quote.get('dias_habiles_entrega', 'No disponible')
            })

        # Correos de Chile
        correos_api = CorreosChileIntegration()
        correos_quote = correos_api.cotizar_envio(
            comuna_origen=origin_commune_code,
            comuna_destino=destination_commune_code,
            kilos=str(max(0.1, total_weight_kg)),
            volumen=str(max(0.00001, total_volume_m3))
        )
        if correos_quote:
            for servicio in correos_quote:
                 if hasattr(servicio, 'Tarifa') and hasattr(servicio, 'Servicio'):
                    shipping_quotes.append({
                        'carrier': 'Correos de Chile',
                        'service_name': getattr(servicio.Servicio, 'Nombre', 'Servicio no especificado'),
                        'price': getattr(servicio.Tarifa, 'Valor', 'N/A'),
                        'delivery_estimate': getattr(servicio, 'PlazoEntrega', 'No disponible')
                    })
        
        return Response(shipping_quotes, status=status.HTTP_200_OK)

class DashboardSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        # 1. Resumen de tarjetas
        total_ventas = Venta.objects.count()
        total_pedidos = Venta.objects.filter(estado_pago='pagado').count() # Asumiendo que 'pedidos' son ventas pagadas
        total_productos = Producto.objects.count()
        total_usuarios = Usuario.objects.count()

        # 2. Datos para gráficos (últimos 30 días)
        t_30_days_ago = timezone.now() - timedelta(days=30)
        
        # Ventas por día
        sales_data = Venta.objects.filter(fecha_v__gte=t_30_days_ago) \
            .annotate(day=TruncDay('fecha_v')) \
            .values('day') \
            .annotate(count=Count('id_venta')) \
            .order_by('day')

        # Ingresos por día
        income_data = Venta.objects.filter(fecha_v__gte=t_30_days_ago, estado_pago='pagado') \
            .annotate(day=TruncDay('fecha_v')) \
            .values('day') \
            .annotate(total=Sum('total_v')) \
            .order_by('day')
        
        # Formatear para el gráfico
        sales_chart = [{'date': item['day'].strftime('%Y-%m-%d'), 'count': item['count']} for item in sales_data]
        income_chart = [{'date': item['day'].strftime('%Y-%m-%d'), 'total': item['total']} for item in income_data]

        # 3. Tabla de ingresos (últimas 10 ventas pagadas)
        recent_incomes = Venta.objects.filter(estado_pago='pagado').order_by('-fecha_v')[:10]
        recent_incomes_serializer = VentaDashboardSerializer(recent_incomes, many=True)

        # Ensamblar respuesta
        summary = {
            'card_summary': {
                'ventas': total_ventas,
                'pedidos': total_pedidos,
                'productos': total_productos,
                'usuarios': total_usuarios
            },
            'charts': {
                'sales': sales_chart,
                'income': income_chart
            },
            'income_table': recent_incomes_serializer.data
        }

        return Response(summary, status=status.HTTP_200_OK)

class OfertaViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar Ofertas.
    Solo accesible por administradores.
    """
    queryset = Oferta.objects.all()
    serializer_class = OfertaSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

class ContactoViewSet(viewsets.ModelViewSet):
    """
    API endpoint para ver y crear mensajes de Contacto.
    - `GET`: Solo accesible por administradores.
    - `POST`: Abierto para crear nuevos mensajes.
    Al crear un mensaje, se envían correos de notificación.
    """
    queryset = Contacto.objects.all()
    serializer_class = ContactoSerializer
    
    def get_permissions(self):
        """
        Permitir a cualquiera crear (POST), pero solo a los administradores
        ver la lista o los detalles (GET).
        """
        if self.action == 'create':
            self.permission_classes = []
        else:
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()

    def perform_create(self, serializer):
        contacto = serializer.save()

        # Enviar correo al admin
        try:
            asunto_admin = f"Nuevo mensaje de contacto: {contacto.asunto}"
            mensaje_admin_html = render_to_string(
                'Tienda/emails/contacto_admin.html',
                {'mensaje': contacto}
            )
            send_mail(
                asunto_admin,
                '', # El mensaje de texto plano se puede omitir si se usa HTML
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                html_message=mensaje_admin_html,
                fail_silently=False,
            )
        except Exception as e:
            # En un entorno de producción, registrar este error
            print(f"Error al enviar correo al admin: {e}")

        # Enviar correo de confirmación al cliente
        try:
            asunto_cliente = "Hemos recibido tu mensaje"
            mensaje_cliente_html = render_to_string(
                'Tienda/emails/contacto_cliente.html',
                {'nombre': contacto.nombre, 'asunto': contacto.asunto}
            )
            send_mail(
                asunto_cliente,
                '',
                settings.DEFAULT_FROM_EMAIL,
                [contacto.correo],
                html_message=mensaje_cliente_html,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error al enviar correo al cliente: {e}")

@api_view(['GET'])
@permission_classes([AllowAny])
def test_connection(request):
    return Response({
        'status': 'success',
        'message': 'Conexión exitosa con el backend'
    })

class ImagenProductoViewSet(viewsets.ModelViewSet):
    queryset = ImagenProducto.objects.all()
    serializer_class = ImagenProductoSerializer
    permission_classes = [IsAdminUser]

class DetalleventaViewSet(viewsets.ModelViewSet):
    queryset = Detalleventa.objects.all()
    serializer_class = DetalleventaSerializer
    permission_classes = [IsAdminUser]

@api_view(['GET'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def current_user(request):
    print('--- /api/auth/me/ ---')
    print('Session key:', request.session.session_key)
    print('Session dict:', dict(request.session))
    print('request.user:', request.user)
    print('request.user.is_authenticated:', request.user.is_authenticated)
    # El usuario autenticado está en request.user
    # Buscar el usuario en el modelo Usuario usando el correo (ajusta si usas otro campo)
    from .models import Usuario
    from .serializers import UsuarioSerializer
    try:
        usuario = Usuario.objects.get(correo_u=request.user.correo_u if hasattr(request.user, 'correo_u') else request.user.email)
        return Response(UsuarioSerializer(usuario).data)
    except Usuario.DoesNotExist:
        return Response({'detail': 'Usuario no encontrado'}, status=404)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@csrf_exempt
def sync_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart = data.get('cart', {})
            print('SYNC_CART recibido:', cart)
            request.session['cart'] = {str(pid): int(qty) for pid, qty in cart.items() if int(qty) > 0}
            print('SYNC_CART guardado en sesión:', request.session['cart'])
            print('SESSION usuario_id:', request.session.get('usuario_id'))
            return JsonResponse({'success': True})
        except Exception as e:
            print('SYNC_CART error:', e)
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@require_GET
@login_required
def mis_ordenes(request):
    usuario = request.user
    ordenes = Venta.objects.filter(usuario=usuario).order_by('-fecha_v')
    data = []
    for orden in ordenes:
        data.append({
            'id_venta': orden.id_venta,
            'fecha_v': orden.fecha_v,
            'total_v': orden.total_v,
            'estado_pago': orden.estado_pago,
        })
    return JsonResponse({'ordenes': data})

@require_POST
@login_required
def actualizar_usuario(request):
    usuario = request.user
    data = json.loads(request.body)
    usuario.nombre_u = data.get('nombre_u', usuario.nombre_u)
    usuario.apellido_u = data.get('apellido_u', usuario.apellido_u)
    usuario.save()
    return JsonResponse({'success': True})

@ensure_csrf_cookie
def get_csrf(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

class WebpayInitiateView(APIView):
    def post(self, request):
        # Espera: {"venta_id": int}
        venta_id = request.data.get('venta_id')
        if not venta_id:
            return Response({'error': 'Falta venta_id'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            venta = Venta.objects.get(id_venta=venta_id)
            return_url = request.build_absolute_uri(reverse('webpay_confirm'))
            tbk = TransbankIntegration()
            response = tbk.create_transaction(venta, return_url)
            return Response({
                'url': response['url'],
                'token': response['token']
            })
        except Venta.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WebpayConfirmView(APIView):
    def post(self, request):
        # Espera: {"token": str}
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Falta token'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tbk = TransbankIntegration()
            result = tbk.commit_transaction(token)
            # El email y actualización de venta ya se manejan en commit_transaction
            return Response({'status': result['status'], 'details': result})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CrearVentaView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        cart = request.data.get('cart', [])
        if not cart or not isinstance(cart, list):
            return Response({'error': 'Carrito vacío o inválido'}, status=400)
        user = request.user
        try:
            total = 0
            venta = Venta.objects.create(
                fecha_v=timezone.now(),
                total_v=0,
                tipo_comprador='usuario',
                usuario=user,
                estado_pago='pendiente'
            )
            for item in cart:
                producto = Producto.objects.get(id_producto=item.product.id_producto)
                cantidad = item.quantity
                subtotal = producto.precio_p * cantidad
                total += subtotal
                Detalleventa.objects.create(
                    id_venta=venta,
                    id_producto=producto,
                    cantidad_dv=cantidad,
                    precio_unitario_dv=producto.precio_p,
                    subtotal_dv=subtotal
                )
                producto.stock_p -= cantidad
                producto.save()
            venta.total_v = total
            venta.save()
            return Response({'venta_id': venta.id_venta})
        except Exception as e:
            return Response({'error': str(e)}, status=500)
