from django import forms
from .models import Producto, Categoria, Usuario, Oferta, Venta, MetodoPago, DireccionUsuario, Contacto, split_rut, ConfiguracionTienda
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'sku', 'nombre_p', 'descripcion_p', 'precio_p', 'stock_p',
            'id_categoria', 'id_oferta',
            'peso_kg', 'alto_cm', 'ancho_cm', 'largo_cm', 'imagen'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU del producto'}),
            'nombre_p': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del producto'}),
            'descripcion_p': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del producto'}),
            'precio_p': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stock_p': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'id_categoria': forms.Select(attrs={'class': 'form-control'}),
            'id_oferta': forms.Select(attrs={'class': 'form-control'}),
            # Puedes agregar widgets personalizados para los nuevos campos si lo deseas
        }

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre_c']
        widgets = {
            'nombre_c': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'}),
        }

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre_u', 'apellido_u', 'numero_telefono_u', 'correo_u', 'tipo_u']
        widgets = {
            'nombre_u': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'apellido_u': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'numero_telefono_u': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'}),
            'correo_u': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
            'tipo_u': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('admin', 'Administrador'),
                ('cliente', 'Cliente'),
            ]),
        }
        help_texts = {
            'nombre_u': 'Nombre del usuario.',
            'apellido_u': 'Apellido del usuario.',
            'numero_telefono_u': 'Número de teléfono de contacto.',
            'correo_u': 'Correo electrónico único del usuario.',
            'tipo_u': 'Tipo de usuario (cliente o administrador).',
        }

class OfertaForm(forms.ModelForm):
    class Meta:
        model = Oferta
        fields = ['descuento', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'style': 'width: 80%; display: inline-block;'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('activa', 'Activa'),
                ('inactiva', 'Inactiva'),
            ]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descuento'].label = 'Descuento (%)'
        self.fields['descuento'].help_text = 'Ingrese solo el número, el símbolo % se mostrará automáticamente.'

class TipoCompradorForm(forms.Form):
    tipo_comprador = forms.ChoiceField(
        choices=[
            ('usuario', 'Usuario Registrado'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='¿Cómo desea realizar su compra?'
    )

class LoginForm(forms.Form):
    correo = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'})
    )
    contrasena = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )

class MetodoPagoForm(forms.Form):
    metodo_pago = forms.ModelChoiceField(
        queryset=MetodoPago.objects.all(),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Seleccione el método de pago',
        empty_label=None
    )

class RegistroUsuarioForm(forms.ModelForm):
    contrasena = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )
    confirmar_contrasena = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
    )
    rut = forms.CharField(
        label='RUT',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RUT (ej: 12345678-9)'})
    )

    class Meta:
        model = Usuario
        fields = ['rut', 'nombre_u', 'apellido_u', 'correo_u', 'numero_telefono_u']
        widgets = {
            'nombre_u': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'apellido_u': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'correo_u': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
            'numero_telefono_u': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        contrasena = cleaned_data.get('contrasena')
        confirmar_contrasena = cleaned_data.get('confirmar_contrasena')
        if contrasena and confirmar_contrasena and contrasena != confirmar_contrasena:
            self.add_error('confirmar_contrasena', 'Las contraseñas no coinciden.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        rut = self.cleaned_data.get('rut')
        if rut:
            rut_numero, rut_dv = split_rut(rut)
            instance.rut_numero = rut_numero
            instance.rut_dv = rut_dv
        if commit:
            instance.save()
        return instance

class DireccionUsuarioForm(forms.ModelForm):
    class Meta:
        model = DireccionUsuario
        fields = [
            'region', 'comuna', 'calle', 'numero',
            'numero_departamento_oficina_otro', 'nombre_receptor', 'telefono_receptor'
        ]
        widgets = {
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Región'}),
            'comuna': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comuna'}),
            'calle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número'}),
            'numero_departamento_oficina_otro': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N° Depto/Oficina/Otro (opcional)'}),
            'nombre_receptor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de quien recibe'}),
            'telefono_receptor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono de quien recibe'}),
        }

class ContactoForm(forms.ModelForm):
    class Meta:
        model = Contacto
        fields = ['nombre', 'correo', 'asunto', 'mensaje']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de ejemplo'
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'calafateaustral@gmail.com'
            }),
            'asunto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Escribe sobre qué quieres hablar'
            }),
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Hola! Quisiera hablar sobre...',
                'rows': 4
            }),
        }

class CustomSuperuserCreationForm(UserCreationForm):
    rut = forms.CharField(
        label='RUT',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RUT (ej: 12345678-9)'})
    )
    nombre_u = forms.CharField(label='Nombre', widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido_u = forms.CharField(label='Apellido', widget=forms.TextInput(attrs={'class': 'form-control'}))
    correo_u = forms.EmailField(label='Correo', widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Usuario
        fields = ('rut', 'nombre_u', 'apellido_u', 'correo_u')

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        # La validación real se hace en el manager, pero puedes agregar validaciones extra aquí si quieres
        return rut

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rut = self.cleaned_data['rut']
        user.nombre_u = self.cleaned_data['nombre_u']
        user.apellido_u = self.cleaned_data['apellido_u']
        user.correo_u = self.cleaned_data['correo_u']
        if commit:
            user.save()
        return user

class ConfiguracionTiendaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionTienda
        fields = '__all__' 