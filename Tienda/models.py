from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator, MinValueValidator
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
import re

# Función para calcular y validar el dígito verificador chileno
def split_rut(rut):
    rut = rut.replace('.', '').replace(' ', '').upper()
    if '-' not in rut and len(rut) > 1:
        rut = rut[:-1] + '-' + rut[-1]
    match = re.match(r'^(\d+)-([\dkK])$', rut)
    if not match:
        raise ValueError('El RUT debe estar en formato 12345678-9')
    numero, dv = match.groups()
    # Validar el dígito verificador
    def calcular_dv(rut_num):
        reversed_digits = map(int, reversed(str(rut_num)))
        factors = [2, 3, 4, 5, 6, 7]
        s = 0
        factor_index = 0
        for d in reversed_digits:
            s += d * factors[factor_index]
            factor_index = (factor_index + 1) % len(factors)
        mod = 11 - (s % 11)
        if mod == 11:
            return '0'
        elif mod == 10:
            return 'K'
        else:
            return str(mod)
    if calcular_dv(numero) != dv:
        raise ValueError('El dígito verificador del RUT no es válido')
    return int(numero), dv

class UsuarioManager(BaseUserManager):
    def create_user(self, correo_u, nombre_u, apellido_u, rut, password=None, **extra_fields):
        rut_numero, rut_dv = split_rut(rut)
        user = self.model(
            correo_u=correo_u,
            nombre_u=nombre_u,
            apellido_u=apellido_u,
            rut_numero=rut_numero,
            rut_dv=rut_dv,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo_u, nombre_u, apellido_u, rut, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('tipo_u', 'admin')
        return self.create_user(correo_u, nombre_u, apellido_u, rut, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    TIPO_CHOICES = [
        ('cliente', 'Cliente'),
        ('admin', 'Administrador'),
    ]
    rut_numero = models.IntegerField(
        db_column='RUT_NUMERO',
        unique=True,
        verbose_name='RUT Número',
        help_text='Número del RUT sin dígito verificador ni guion'
    )
    rut_dv = models.CharField(
        db_column='RUT_DV',
        max_length=1,
        verbose_name='Dígito Verificador',
        help_text='Dígito verificador del RUT'
    )
    nombre_u = models.CharField(db_column='Nombre_U', max_length=100, verbose_name='Nombre Usuario')
    apellido_u = models.CharField(db_column='Apellido_U', max_length=100, verbose_name='Apellido Usuario')
    numero_telefono_u = models.CharField(
        db_column='Numero_telefono_U', 
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?56?\d{9,15}$',
                message='Ingrese un número chileno válido (+56912345678 o 912345678)'
            )
        ],
        verbose_name='Número Teléfono'
    )
    correo_u = models.EmailField(
        db_column='Correo_U', 
        max_length=100, 
        unique=True,
        verbose_name='Correo Usuario'
    )
    tipo_u = models.CharField(
        db_column='Tipo_U', 
        max_length=10, 
        choices=TIPO_CHOICES, 
        default='cliente',
        verbose_name='Tipo Usuario'
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    password = models.CharField(max_length=128, default='')

    USERNAME_FIELD = 'correo_u'
    REQUIRED_FIELDS = ['nombre_u', 'apellido_u', 'rut_numero', 'rut_dv']

    objects = UsuarioManager()

    class Meta:
        db_table = 'USUARIO'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.rut_usuario} - {self.nombre_u} {self.apellido_u}"

    @property
    def rut_usuario(self):
        return f"{self.rut_numero}-{self.rut_dv}"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

class MetodoPago(models.Model):
    id_metodo = models.AutoField(db_column='ID_Metodo', primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'METODO_PAGO'

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    id_categoria = models.AutoField(db_column='ID_Categoria', primary_key=True)
    nombre_c = models.CharField(db_column='Nombre_C', max_length=100)

    class Meta:
        db_table = 'CATEGORIA'

    def __str__(self):
        return self.nombre_c


class Oferta(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('no_activo', 'No Activo'),
    ]
    id_oferta = models.AutoField(db_column='ID_Oferta', primary_key=True)
    descuento = models.DecimalField(db_column='Descuento', max_digits=5, decimal_places=2)
    fecha_inicio = models.DateField(db_column='Fecha_inicio')
    fecha_fin = models.DateField(db_column='Fecha_fin')
    estado = models.CharField(db_column='Estado', max_length=10, choices=ESTADO_CHOICES)

    class Meta:
        db_table = 'OFERTA'

    def __str__(self):
        return f"{self.descuento}% - {self.estado}"


class Producto(models.Model):
    id_producto = models.AutoField(
        db_column='ID_Producto', 
        primary_key=True,
        verbose_name='ID Producto'
    )
    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='SKU',
        help_text='Código de Referencia Único (SKU) del producto'
    )
    nombre_p = models.CharField(
        db_column='Nombre_P', 
        max_length=100,
        verbose_name='Nombre Producto'
    )
    descripcion_p = models.TextField(
        db_column='Descripcion_P', 
        blank=True, 
        null=True,
        verbose_name='Descripción Producto'
    )
    precio_p = models.IntegerField(
        db_column='Precio_P',
        verbose_name='Precio Producto'
    )  # Precio en pesos chilenos (números enteros)
    stock_p = models.IntegerField(
        db_column='Stock_P',
        verbose_name='Stock Producto',
        validators=[MinValueValidator(0, message='El stock no puede ser un número negativo.')]
    )
    
    # Dimensiones y peso para envíos
    peso_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01, message='El peso debe ser positivo.')],
        verbose_name='Peso (kg)',
        help_text='Peso del producto en kilogramos.'
    )
    alto_cm = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1, message='El alto debe ser positivo.')],
        verbose_name='Alto (cm)',
        help_text='Alto del producto en centímetros.'
    )
    ancho_cm = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1, message='El ancho debe ser positivo.')],
        verbose_name='Ancho (cm)',
        help_text='Ancho del producto en centímetros.'
    )
    largo_cm = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1, message='El largo debe ser positivo.')],
        verbose_name='Largo (cm)',
        help_text='Largo del producto en centímetros.'
    )

    id_categoria = models.ForeignKey(
        Categoria, 
        models.DO_NOTHING, 
        db_column='ID_Categoria', 
        blank=True, 
        null=True,
        verbose_name='Categoría'
    )
    id_oferta = models.ForeignKey(
        Oferta, 
        models.DO_NOTHING, 
        db_column='ID_Oferta', 
        blank=True, 
        null=True,
        verbose_name='Oferta'
    )
    imagen = models.ImageField(
        upload_to='productos/', 
        blank=True, 
        null=True,
        verbose_name='Imagen Principal'
    )

    class Meta:
        db_table = 'PRODUCTO'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return f"ID: {self.id_producto} - {self.nombre_p}"

    def precio_con_descuento(self):
        """Calcula el precio con descuento si el producto tiene una oferta activa"""
        if self.id_oferta and self.id_oferta.estado == 'activo':
            descuento = self.id_oferta.descuento
            return int(self.precio_p * (1 - descuento / 100))
        return self.precio_p

    def tiene_oferta_activa(self):
        """Verifica si el producto tiene una oferta activa"""
        return self.id_oferta and self.id_oferta.estado == 'activo'


class Venta(models.Model):
    TIPO_COMPRADOR_CHOICES = [
        ('usuario', 'Usuario Registrado'),
    ]
    ESTADO_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('rechazado', 'Rechazado'),
        ('cancelado', 'Cancelado'),
    ]
    
    id_venta = models.AutoField(db_column='ID_Venta', primary_key=True)
    fecha_v = models.DateField(db_column='Fecha_V')
    total_v = models.DecimalField(db_column='Total_V', max_digits=10, decimal_places=2)
    tipo_comprador = models.CharField(max_length=10, choices=TIPO_COMPRADOR_CHOICES, null=True, blank=True)
    usuario = models.ForeignKey(
        Usuario, 
        models.DO_NOTHING, 
        db_column='ID_USUARIO', 
        to_field='id',
        blank=True, 
        null=True
    )
    id_metodo = models.ForeignKey('MetodoPago', models.DO_NOTHING, db_column='ID_Metodo', blank=True, null=True)
    
    # Campos para procesamiento de pagos con Getnet
    estado_pago = models.CharField(
        max_length=20, 
        choices=ESTADO_PAGO_CHOICES, 
        default='pendiente',
        verbose_name='Estado del Pago'
    )
    transaction_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name='ID de Transacción Getnet'
    )
    fecha_pago = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name='Fecha de Pago'
    )
    checkout_session_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name='ID de Sesión de Checkout'
    )
    webhook_data = models.JSONField(
        blank=True, 
        null=True,
        verbose_name='Datos del Webhook'
    )

    class Meta:
        db_table = 'VENTA'
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'

    def __str__(self):
        return f"Venta #{self.id_venta} - {self.fecha_v} - {self.estado_pago}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.usuario:
            raise ValidationError('Se requiere un usuario registrado para este tipo de venta')

class Detalleventa(models.Model):
    ESTADO_ENVIO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_preparacion', 'En Preparación'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    id_detalleventa = models.AutoField(db_column='ID_DetalleVenta', primary_key=True)
    cantidad_dv = models.IntegerField(db_column='Cantidad_DV')
    precio_unitario_dv = models.DecimalField(db_column='Precio_unitario_DV', max_digits=10, decimal_places=2)
    subtotal_dv = models.DecimalField(db_column='Subtotal_DV', max_digits=10, decimal_places=2)
    id_venta = models.ForeignKey(Venta, models.CASCADE, db_column='ID_Venta', blank=True, null=True)
    id_producto = models.ForeignKey(Producto, models.DO_NOTHING, db_column='ID_Producto', blank=True, null=True)
    
    # Nuevos campos para el envío
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_ENVIO_CHOICES,
        default='pendiente',
        verbose_name='Estado del Envío'
    )
    numero_seguimiento = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Número de Seguimiento'
    )

    class Meta:
        db_table = 'DETALLEVENTA'

    def __str__(self):
        return f"Detalle #{self.id_detalleventa} - {self.id_producto}"

class DireccionUsuario(models.Model):
    id_direccion_usuario = models.AutoField(db_column='ID_Direccion_Usuario', primary_key=True)
    usuario = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column='ID_USUARIO',
        to_field='id',
        related_name='direcciones'
    )
    region = models.CharField(db_column='Region', max_length=100)
    comuna = models.CharField(db_column='Comuna', max_length=100)
    calle = models.CharField(db_column='Calle', max_length=100)
    numero = models.CharField(db_column='Numero', max_length=10)
    numero_departamento_oficina_otro = models.CharField(db_column='Numero_Departamento_Oficina_Otro', max_length=50, blank=True, null=True)
    nombre_receptor = models.CharField(db_column='Nombre_Receptor', max_length=100)
    telefono_receptor = models.CharField(db_column='Telefono_Receptor', max_length=20)

    class Meta:
        db_table = 'DIRECCION_USUARIO'
        verbose_name = 'Dirección de Usuario'
        verbose_name_plural = 'Direcciones de Usuario'

    def __str__(self):
        return f"{self.usuario} - {self.region}, {self.comuna}, {self.calle} {self.numero}"

class ImagenProducto(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='productos/')
    descripcion = models.CharField(max_length=200, blank=True, null=True, help_text='Descripción opcional de la imagen')
    orden = models.IntegerField(default=0, help_text='Orden de aparición de la imagen')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'IMAGEN_PRODUCTO'
        verbose_name = 'Imagen de Producto'
        verbose_name_plural = 'Imágenes de Productos'
        ordering = ['orden', 'fecha_subida']

    def __str__(self):
        return f"Imagen {self.id_imagen} del producto {self.producto.nombre_p}"

class Contacto(models.Model):
    id_contacto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    correo = models.EmailField(max_length=100, verbose_name='Correo electrónico')
    asunto = models.CharField(max_length=200, verbose_name='Asunto')
    mensaje = models.TextField(verbose_name='Mensaje')
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de envío')
    leido = models.BooleanField(default=False, verbose_name='Leído')

    class Meta:
        db_table = 'CONTACTO'
        verbose_name = 'Mensaje de Contacto'
        verbose_name_plural = 'Mensajes de Contacto'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.asunto} - {self.nombre} ({self.fecha.strftime('%d/%m/%Y %H:%M')})"

class ConfiguracionTienda(models.Model):
    nombre = models.CharField(max_length=200, default='Calafate Austral', verbose_name='Nombre de la tienda')
    logo = models.ImageField(upload_to='config/', blank=True, null=True, verbose_name='Logo')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    email = models.EmailField(max_length=100, blank=True, null=True, verbose_name='Email de contacto')
    telefono = models.CharField(max_length=30, blank=True, null=True, verbose_name='Teléfono')
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name='Dirección')
    politica_envio = models.TextField(blank=True, null=True, verbose_name='Política de Envíos')
    politica_devolucion = models.TextField(blank=True, null=True, verbose_name='Política de Devoluciones')
    politica_privacidad = models.TextField(blank=True, null=True, verbose_name='Política de Privacidad')
    terminos = models.TextField(blank=True, null=True, verbose_name='Términos y Condiciones')
    metodo_pago = models.CharField(max_length=100, blank=True, null=True, verbose_name='Método de Pago Principal')
    credencial_pago = models.CharField(max_length=255, blank=True, null=True, verbose_name='Credencial de Pago')
    servicio_envio = models.CharField(max_length=100, blank=True, null=True, verbose_name='Servicio de Envío')
    webhook = models.CharField(max_length=255, blank=True, null=True, verbose_name='Webhook/Integración')
    color_primario = models.CharField(max_length=7, blank=True, null=True, verbose_name='Color Primario (hex)')
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración de la Tienda'
        verbose_name_plural = 'Configuración de la Tienda'

    def save(self, *args, **kwargs):
        self.pk = 1  # Forzar siempre el mismo ID
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj