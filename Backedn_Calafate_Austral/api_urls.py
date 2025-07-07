from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Tienda.api_views import (
    UsuarioViewSet, VentaViewSet, ProductoViewSet, CategoriaViewSet, CheckoutView, 
    ShippingQuoteView, DashboardSummaryView, OfertaViewSet, ContactoViewSet, ImagenProductoViewSet, DetalleventaViewSet,
    current_user,
    CustomTokenObtainPairView,
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'ventas', VentaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'categorias', CategoriaViewSet)
router.register(r'ofertas', OfertaViewSet)
router.register(r'contactos', ContactoViewSet)
router.register(r'imagenes-producto', ImagenProductoViewSet)
router.register(r'detalleventas', DetalleventaViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('shipping/quote/', ShippingQuoteView.as_view(), name='shipping-quote'),
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('auth/me/', current_user, name='current_user'),
] 