from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    ProductoViewSet,
    test_connection,
    current_user,
    sync_cart,
    mis_ordenes,
    actualizar_usuario,
    get_csrf,
)
from . import views
from django.urls import reverse
from django.urls import reverse_lazy
from django.urls import path
from django.urls import re_path
from django.urls import include


router = DefaultRouter()
router.register(r'productos', ProductoViewSet)

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    path('api/test/', test_connection, name='test-connection'),
    path('api/auth/me/', current_user, name='current_user'),
    path('api/csrf/', get_csrf, name='get_csrf'),
    path('api/sync-cart/', sync_cart, name='sync_cart'),
    path('api/mis-ordenes/', mis_ordenes, name='mis_ordenes'),
    path('api/actualizar-usuario/', actualizar_usuario, name='actualizar_usuario'),

    # Vista URLs
    path('', views.home, name='home'),
    path('producto/<str:sku>/', views.producto_detalle, name='producto_detalle'),
    
    # URLs públicas (para usuarios normales)
    path('compra/login/', views.login_compra, name='login_compra'),
    path('compra/metodo-pago/', views.metodo_pago, name='metodo_pago'),
    path('compra/confirmar/', views.confirmar_compra, name='confirmar_compra'),
    path('compra/logout/', views.logout_cliente, name='logout_cliente'),
    path('compra/registro-usuario/', views.registro_usuario, name='registro_usuario'),
    
    # URLs para pagos con Getnet
    path('compra/getnet-checkout/', views.getnet_checkout, name='getnet_checkout'),
    path('getnet/confirmation/', views.getnet_confirmation, name='getnet_confirmation'),
    path('getnet/cancel/', views.getnet_cancel, name='getnet_cancel'),
    path('getnet/webhook/', views.getnet_webhook, name='getnet_webhook'),
    path('getnet/payment-status/<int:venta_id>/', views.getnet_payment_status, name='getnet_payment_status'),
    
    # URLs para administradores
    path('panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('panel/productos/', views.admin_productos, name='admin_productos'),
    path('panel/productos/crear/', views.admin_producto_crear, name='admin_producto_crear'),
    path('panel/productos/<int:producto_id>/editar/', views.admin_producto_editar, name='admin_producto_editar'),
    path('panel/productos/<int:producto_id>/eliminar/', views.admin_producto_eliminar, name='admin_producto_eliminar'),
    path('panel/categorias/', views.admin_categorias, name='admin_categorias'),
    path('panel/categorias/<int:categoria_id>/eliminar/', views.admin_categoria_eliminar, name='admin_categoria_eliminar'),
    path('panel/ventas/', views.admin_ventas, name='admin_ventas'),
    path('panel/ventas/<int:venta_id>/', views.admin_venta_detalle, name='admin_venta_detalle'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/add/<str:sku>/', views.add_to_cart, name='add_to_cart'),
    path('carrito/remove/<str:sku>/', views.remove_from_cart, name='remove_from_cart'),
    path('contacto/', views.contacto, name='contacto'),
    path('compra/metodo-pago-api/', views.set_payment_method, name='set_payment_method_api'),
    path('panel/ofertas/', views.admin_ofertas, name='admin_ofertas'),
    path('panel/ofertas/crear/', views.admin_oferta_crear, name='admin_oferta_crear'),
    path('panel/ofertas/<int:oferta_id>/editar/', views.admin_oferta_editar, name='admin_oferta_editar'),
    path('panel/ofertas/<int:oferta_id>/eliminar/', views.admin_oferta_eliminar, name='admin_oferta_eliminar'),
    path('panel/mensajes/', views.admin_mensajes, name='admin_mensajes'),
    path('panel/mensajes/<int:mensaje_id>/', views.admin_mensaje_detalle, name='admin_mensaje_detalle'),
    path('panel/mensajes/<int:mensaje_id>/marcar_leido/', views.admin_mensaje_marcar_leido, name='admin_mensaje_marcar_leido'),
    path('panel/mensajes/<int:mensaje_id>/marcar_no_leido/', views.admin_mensaje_marcar_no_leido, name='admin_mensaje_marcar_no_leido'),
    path('panel/mensajes/<int:mensaje_id>/eliminar/', views.admin_mensaje_eliminar, name='admin_mensaje_eliminar'),
    path('panel/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('panel/usuarios/crear/', views.admin_usuario_crear, name='admin_usuario_crear'),
    path('panel/usuarios/<int:usuario_id>/editar/', views.admin_usuario_editar, name='admin_usuario_editar'),
    path('panel/usuarios/<int:usuario_id>/eliminar/', views.admin_usuario_eliminar, name='admin_usuario_eliminar'),
    path('panel/configuracion/', views.admin_configuracion, name='admin_configuracion'),
] 

# --- API endpoints para compra bajo /api/ ---
api_patterns = [
    path('compra/login/', views.login_compra, name='api_login_compra'),
    path('compra/registro-usuario/', views.registro_usuario, name='api_registro_usuario'),
    path('compra/logout/', views.logout_cliente, name='api_logout_cliente'),
]

urlpatterns += [
    path('api/', include(api_patterns)),
] 
