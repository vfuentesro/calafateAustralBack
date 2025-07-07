from rest_framework import serializers
from .models import Producto, Categoria, Venta, Usuario, Oferta, Contacto, ImagenProducto, Detalleventa
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class OfertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Oferta
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            'id', 'correo_u', 'nombre_u', 'apellido_u', 'is_superuser',
            # Agrega aquí otros campos que quieras exponer
        ]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = super().create(validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance

class VentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venta
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    id_oferta = OfertaSerializer(read_only=True)
    discount = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = '__all__'

    def get_discount(self, obj):
        # Si el producto tiene una oferta activa, retorna el descuento, si no, 0
        if obj.id_oferta and getattr(obj.id_oferta, 'estado', None) == 'activo':
            return getattr(obj.id_oferta, 'descuento', 0)
        return 0

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class VentaDashboardSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = ['id_venta', 'fecha_v', 'total_v', 'estado_pago', 'cliente_nombre']
    
    def get_cliente_nombre(self, obj):
        if obj.id_usuario:
            return f"{obj.id_usuario.nombre_u} {obj.id_usuario.apellido_u}"
        return "Invitado"

class CartItemSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=50)
    quantity = serializers.IntegerField(min_value=1)

class CartSerializer(serializers.Serializer):
    cart = CartItemSerializer(many=True)

class ContactoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contacto
        fields = '__all__'
        read_only_fields = ['fecha']

class ImagenProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenProducto
        fields = '__all__'

class DetalleventaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detalleventa
        fields = '__all__'

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'correo_u' 