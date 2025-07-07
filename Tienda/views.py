from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST
from .models import Producto, Categoria, Usuario, Venta, Detalleventa, MetodoPago, Contacto, Oferta, ConfiguracionTienda
from .forms import ProductoForm, CategoriaForm, UsuarioForm, OfertaForm, TipoCompradorForm, LoginForm, MetodoPagoForm, RegistroUsuarioForm, DireccionUsuarioForm, ContactoForm, ConfiguracionTiendaForm
from .getnet_integration import GetnetIntegration
import json
import logging
from django.urls import reverse
from collections import OrderedDict
import calendar
from django.contrib.auth import authenticate, login as auth_login
from django.core.cache import cache

logger = logging.getLogger(__name__)

def is_admin(user):
    """Verifica si el usuario es administrador"""
    return user.is_authenticated and user.is_staff

def home(request):
    """Página principal - muestra productos para usuarios normales"""
    productos = Producto.objects.filter(stock_p__gt=0).order_by('-id_producto')
    categorias = Categoria.objects.all()
    
    # Filtros
    categoria_id = request.GET.get('categoria')
    busqueda = request.GET.get('busqueda')
    
    if categoria_id:
        productos = productos.filter(id_categoria_id=categoria_id)
    
    if busqueda:
        productos = productos.filter(
            Q(nombre_p__icontains=busqueda) | 
            Q(descripcion_p__icontains=busqueda)
        )
    
    # Paginación
    paginator = Paginator(productos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Detectar si el usuario es superuser Django o admin del modelo personalizado
    es_admin = False
    if request.user.is_authenticated and request.user.is_superuser:
        es_admin = True
    elif request.session.get('usuario_id'):
        try:
            usuario = Usuario.objects.get(id=request.session['usuario_id'])
            if usuario.tipo_u == 'admin':
                es_admin = True
        except Usuario.DoesNotExist:
            pass

    context = {
        'productos': page_obj,
        'categorias': categorias,
        'categoria_actual': categoria_id,
        'busqueda': busqueda,
        'es_admin': es_admin,
    }
    return render(request, 'Tienda/home.html', context)

def producto_detalle(request, sku):
    """Muestra el detalle de un producto específico."""
    producto = get_object_or_404(Producto, sku=sku)
    
    context = {
        'producto': producto,
    }
    return render(request, 'Tienda/producto_detalle.html', context)

# Vistas para administradores
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Dashboard del administrador"""
    total_productos = Producto.objects.count()
    total_ventas = Venta.objects.count()
    total_usuarios = Usuario.objects.count()
    productos_bajo_stock = Producto.objects.filter(stock_p__lt=10)
    total_ofertas = Oferta.objects.count()
    
    # Ventas e ingresos por mes (últimos 12 meses)
    today = timezone.now().date()
    months = []
    ventas_por_mes = []
    ingresos_por_mes = []
    for i in range(11, -1, -1):
        month = (today.replace(day=1) - timezone.timedelta(days=30*i)).replace(day=1)
        year = month.year
        month_num = month.month
        label = f"{calendar.month_abbr[month_num]} {year}"
        months.append(label)
        ventas = Venta.objects.filter(fecha_v__year=year, fecha_v__month=month_num).count()
        ingresos = Venta.objects.filter(fecha_v__year=year, fecha_v__month=month_num, estado_pago='pagado').aggregate(total=Sum('total_v'))['total'] or 0
        ventas_por_mes.append(ventas)
        ingresos_por_mes.append(float(ingresos))
    months = months[::-1]
    ventas_por_mes = ventas_por_mes[::-1]
    ingresos_por_mes = ingresos_por_mes[::-1]
    # Productos más vendidos (top 5)
    top_productos = (
        Detalleventa.objects.values('id_producto__nombre_p')
        .annotate(total_vendidos=Sum('cantidad_dv'))
        .order_by('-total_vendidos')[:5]
    )
    productos_labels = [p['id_producto__nombre_p'] for p in top_productos]
    productos_data = [p['total_vendidos'] for p in top_productos]
    # Nuevos usuarios por mes (últimos 12 meses)
    usuarios_por_mes = []
    for i in range(11, -1, -1):
        month = (today.replace(day=1) - timezone.timedelta(days=30*i)).replace(day=1)
        year = month.year
        month_num = month.month
        count = Usuario.objects.filter(date_joined__year=year, date_joined__month=month_num).count()
        usuarios_por_mes.append(count)
    usuarios_por_mes = usuarios_por_mes[::-1]
    
    context = {
        'total_productos': total_productos,
        'total_ventas': total_ventas,
        'total_usuarios': total_usuarios,
        'productos_bajo_stock': productos_bajo_stock,
        'total_ofertas': total_ofertas,
        # Gráficas
        'months': months,
        'ventas_por_mes': ventas_por_mes,
        'ingresos_por_mes': ingresos_por_mes,
        'productos_labels': productos_labels,
        'productos_data': productos_data,
        'usuarios_por_mes': usuarios_por_mes,
    }
    return render(request, 'Tienda/admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_productos(request):
    """Lista de productos para administradores"""
    productos = Producto.objects.all().order_by('-id_producto')
    
    # Filtros
    categoria_id = request.GET.get('categoria')
    busqueda = request.GET.get('busqueda')
    
    if categoria_id:
        productos = productos.filter(id_categoria_id=categoria_id)
    
    if busqueda:
        productos = productos.filter(
            Q(nombre_p__icontains=busqueda) | 
            Q(descripcion_p__icontains=busqueda)
        )
    
    # Paginación
    paginator = Paginator(productos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categorias = Categoria.objects.all()
    
    context = {
        'productos': page_obj,
        'categorias': categorias,
        'categoria_actual': categoria_id,
        'busqueda': busqueda,
    }
    return render(request, 'Tienda/admin/productos.html', context)

@login_required
@user_passes_test(is_admin)
def admin_producto_crear(request):
    """Crear nuevo producto"""
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        print("[CREAR] Form valido:", form.is_valid())
        print("[CREAR] Errores:", form.errors)
        if form.is_valid():
            form.save()
            print("[CREAR] Producto guardado correctamente")
            messages.success(request, 'Producto creado exitosamente.')
            return redirect('admin_productos')
        else:
            print("[CREAR] No se guardó el producto")
    else:
        form = ProductoForm()
    
    context = {
        'form': form,
        'titulo': 'Crear Producto',
    }
    return render(request, 'Tienda/admin/producto_form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_producto_editar(request, producto_id):
    """Editar producto existente"""
    producto = get_object_or_404(Producto, id_producto=producto_id)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        print("[EDITAR] Form valido:", form.is_valid())
        print("[EDITAR] Errores:", form.errors)
        if form.is_valid():
            form.save()
            print("[EDITAR] Producto guardado correctamente")
            messages.success(request, 'Producto actualizado exitosamente.')
            return redirect('admin_productos')
        else:
            print("[EDITAR] No se guardó el producto")
    else:
        form = ProductoForm(instance=producto)
    
    context = {
        'form': form,
        'producto': producto,
        'titulo': 'Editar Producto',
    }
    return render(request, 'Tienda/admin/producto_form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_producto_eliminar(request, producto_id):
    """Eliminar producto"""
    producto = get_object_or_404(Producto, id_producto=producto_id)
    
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado exitosamente.')
        return redirect('admin_productos')
    
    context = {
        'producto': producto,
    }
    return render(request, 'Tienda/admin/producto_confirmar_eliminar.html', context)

@login_required
@user_passes_test(is_admin)
def admin_categorias(request):
    """Gestión de categorías"""
    categorias = Categoria.objects.all().order_by('nombre_c')
    
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría creada exitosamente.')
            return redirect('admin_categorias')
    else:
        form = CategoriaForm()
    
    context = {
        'categorias': categorias,
        'form': form,
    }
    return render(request, 'Tienda/admin/categorias.html', context)

@login_required
@user_passes_test(is_admin)
def admin_categoria_eliminar(request, categoria_id):
    """Eliminar categoría"""
    categoria = get_object_or_404(Categoria, id_categoria=categoria_id)
    
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoría eliminada exitosamente.')
        return redirect('admin_categorias')
    
    context = {
        'categoria': categoria,
    }
    return render(request, 'Tienda/admin/categoria_confirmar_eliminar.html', context)

@login_required
@user_passes_test(is_admin)
def admin_ventas(request):
    """Lista de ventas"""
    ventas = Venta.objects.all().order_by('-fecha_v')
    
    # Paginación
    paginator = Paginator(ventas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'ventas': page_obj,
    }
    return render(request, 'Tienda/admin/ventas.html', context)

@login_required
@user_passes_test(is_admin)
def admin_venta_detalle(request, venta_id):
    """Detalle de una venta"""
    venta = get_object_or_404(Venta, id_venta=venta_id)
    detalles = Detalleventa.objects.filter(id_venta=venta)
    
    context = {
        'venta': venta,
        'detalles': detalles,
    }
    return render(request, 'Tienda/admin/venta_detalle.html', context)

@csrf_exempt
def login_compra(request):
    """Login para usuarios registrados y superusers Django, con rate limiting y mensajes genéricos"""
    next_url = request.GET.get('next', '')
    ip = request.META.get('REMOTE_ADDR')
    fail_key = f'login_fails_{ip}'
    fail_count = cache.get(fail_key, 0)
    blocked = fail_count >= 5
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if request.method == 'POST':
        if blocked:
            if is_ajax:
                return JsonResponse({'detail': 'Demasiados intentos fallidos. Intenta de nuevo más tarde.'}, status=400)
            messages.error(request, 'Demasiados intentos fallidos. Intenta de nuevo más tarde.')
        else:
            form = LoginForm(request.POST)
            if form.is_valid():
                correo = form.cleaned_data['correo']
                contrasena = form.cleaned_data['contrasena']
                user = authenticate(request, username=correo, password=contrasena)
                if user is not None and user.is_superuser:
                    auth_login(request, user)
                    cache.delete(fail_key)
                    if is_ajax:
                        return JsonResponse({'success': True, 'is_superuser': True, 'user': user.correo_u}, status=200)
                    return redirect('admin_dashboard')
                try:
                    usuario = Usuario.objects.get(correo_u=correo)
                    if usuario.check_password(contrasena):
                        request.session['usuario_id'] = usuario.id
                        cache.delete(fail_key)
                        auth_login(request, usuario)
                        if is_ajax:
                            return JsonResponse({'success': True, 'user_id': usuario.id, 'nombre_u': usuario.nombre_u, 'is_superuser': False}, status=200)
                        if usuario.tipo_u == 'admin':
                            return redirect('admin_dashboard')
                        if next_url:
                            return redirect(next_url)
                        return redirect('metodo_pago')
                except Usuario.DoesNotExist:
                    pass
                # Si llega aquí, es fallo
                fail_count += 1
                cache.set(fail_key, fail_count, timeout=600)  # 10 minutos
                if is_ajax:
                    return JsonResponse({'detail': 'Credenciales inválidas.'}, status=400)
                if fail_count >= 5:
                    messages.error(request, 'Demasiados intentos fallidos. Intenta de nuevo más tarde.')
                else:
                    messages.error(request, 'Credenciales inválidas.')
            else:
                if is_ajax:
                    return JsonResponse({'detail': 'Credenciales inválidas.'}, status=400)
                messages.error(request, 'Credenciales inválidas.')
    else:
        form = LoginForm()
    if is_ajax:
        return JsonResponse({'detail': 'Método no permitido.'}, status=405)
    return render(request, 'Tienda/compra/login.html', {
        'form': form,
        'next': next_url
    })

def registro_invitado(request):
    """Registro de datos para compradores invitados"""
    if request.method == 'POST':
        form = InvitadoForm(request.POST)
        if form.is_valid():
            invitado = form.save()
            request.session['invitado_id'] = invitado.id_invitado
            return redirect('metodo_pago')
    else:
        form = InvitadoForm()
    
    return render(request, 'Tienda/compra/registro_invitado.html', {'form': form})

def metodo_pago(request):
    """Selección del método de pago"""
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'El carrito está vacío.')
        return redirect('ver_carrito')
        
    if request.method == 'POST':
        form = MetodoPagoForm(request.POST)
        if form.is_valid():
            metodo_pago_obj = form.cleaned_data['metodo_pago']
            request.session['metodo_pago'] = metodo_pago_obj.id_metodo
            
            # Redirigir según el método de pago
            if 'getnet' in metodo_pago_obj.nombre.lower():
                return redirect('getnet_checkout')
            else: # Asumir transferencia u otros métodos que usan el flujo de confirmación
                return redirect('confirmar_compra')
    else:
        form = MetodoPagoForm()
    
    return render(request, 'Tienda/compra/metodo_pago.html', {'form': form})

def confirmar_compra(request):
    """Confirmación final de la compra y guardado en la base de datos"""
    metodo_pago_id = request.session.get('metodo_pago')
    metodo_pago = None
    if metodo_pago_id:
        try:
            metodo_pago = MetodoPago.objects.get(id_metodo=metodo_pago_id)
        except MetodoPago.DoesNotExist:
            metodo_pago = None

    if not metodo_pago:
        messages.error(request, 'Por favor complete todos los pasos del proceso de compra')
        return redirect('ver_carrito')

    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        messages.error(request, 'Por favor inicie sesión')
        return redirect('login_compra')
    
    try:
        comprador = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        # El usuario de la sesión ya no existe, probablemente por el reinicio de la BD
        if 'usuario_id' in request.session:
            del request.session['usuario_id']
        messages.error(request, 'Tu sesión ha expirado. Por favor, inicia sesión de nuevo.')
        return redirect('login_compra')

    # Obtener productos del carrito
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'El carrito está vacío.')
        return redirect('ver_carrito')

    # Optimización: Obtener todos los productos en una sola consulta
    product_ids = [int(pid) for pid in cart.keys()]
    productos_en_carrito = Producto.objects.in_bulk(product_ids)
    
    total = 0
    detalles = []

    # Optimización: Un solo bucle para verificar stock y preparar detalles
    # Usar list() para poder modificar el diccionario mientras se itera
    for pid_str, cantidad in list(cart.items()):
        producto_id = int(pid_str)
        producto = productos_en_carrito.get(producto_id)

        if not producto:
            messages.warning(request, f'Un producto en tu carrito ya no existe y ha sido eliminado.')
            del cart[pid_str]
            # No se redirige para permitir que la compra continúe con los otros productos
            continue

        if cantidad > producto.stock_p:
            messages.error(request, f"No hay suficiente stock para '{producto.nombre_p}'. Solo quedan {producto.stock_p} unidades. Por favor, ajusta tu carrito.")
            return redirect('ver_carrito')

        precio_unitario = producto.precio_con_descuento()
        subtotal = precio_unitario * cantidad
        total += subtotal
        detalles.append({
            'producto': producto,
            'cantidad': cantidad,
            'precio_unitario': precio_unitario,
            'subtotal': subtotal
        })

    # Si después de limpiar productos no válidos el carrito queda vacío
    if not detalles:
        messages.error(request, 'No quedan productos válidos en tu carrito.')
        request.session['cart'] = cart
        return redirect('ver_carrito')


    # Crear la venta
    venta = Venta.objects.create(
        fecha_v=timezone.now(),
        total_v=total,
        tipo_comprador='usuario',
        usuario=comprador,
        id_metodo=metodo_pago,
        estado_pago='pendiente'
    )

    # Crear los detalles de venta y descontar stock
    for item in detalles:
        Detalleventa.objects.create(
            cantidad_dv=item['cantidad'],
            precio_unitario_dv=item['precio_unitario'],
            subtotal_dv=item['subtotal'],
            id_venta=venta,
            id_producto=item['producto']
        )
        # Descontar stock
        item['producto'].stock_p -= item['cantidad']
        item['producto'].save(update_fields=['stock_p'])

    # Limpiar carrito
    request.session['cart'] = {}
    request.session['metodo_pago'] = None

    # Obtener detalles para mostrar
    detalles_venta = Detalleventa.objects.filter(id_venta=venta)

    # Obtener dirección de envío
    direccion_envio = comprador.direcciones.first()

    context = {
        'comprador': comprador,
        'direccion_envio': direccion_envio,
        'metodo_pago': metodo_pago,
        'venta': venta,
        'detalles_venta': detalles_venta,
    }
    return render(request, 'Tienda/compra/confirmar.html', context)

def registro_usuario(request):
    """Registro de usuario nuevo con dirección obligatoria y sincronización de direccion_envio"""
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        direccion_form = DireccionUsuarioForm(request.POST)
        if form.is_valid() and direccion_form.is_valid():
            usuario = form.save(commit=False)
            usuario.tipo_u = 'cliente'
            usuario.set_password(form.cleaned_data['contrasena'])
            usuario.save()
            direccion = direccion_form.save(commit=False)
            direccion.usuario = usuario
            direccion.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({'success': True, 'message': 'Usuario registrado correctamente.'})
            else:
                messages.success(request, 'Usuario y dirección registrados exitosamente. Ahora puede iniciar sesión.')
                return redirect('login_compra')
        else:
            errors = {**form.errors, **direccion_form.errors}
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        form = RegistroUsuarioForm()
        direccion_form = DireccionUsuarioForm()
    return render(request, 'Tienda/compra/registro_usuario.html', {'form': form, 'direccion_form': direccion_form})

def logout_cliente(request):
    request.session.flush()
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('home')

def add_to_cart(request, sku):
    producto = get_object_or_404(Producto, sku=sku)
    cantidad = int(request.POST.get('cantidad', 1))
    if cantidad < 1:
        cantidad = 1
    if cantidad > producto.stock_p:
        cantidad = producto.stock_p
    cart = request.session.get('cart', {})
    cart[str(producto.id_producto)] = min(cart.get(str(producto.id_producto), 0) + cantidad, producto.stock_p)
    request.session['cart'] = cart
    messages.success(request, f'Se añadieron {cantidad} de {producto.nombre_p} al carrito.')
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('ver_carrito')

def remove_from_cart(request, sku):
    producto = get_object_or_404(Producto, sku=sku)
    cart = request.session.get('cart', {})
    if str(producto.id_producto) in cart:
        del cart[str(producto.id_producto)]
        request.session['cart'] = cart
        messages.success(request, 'Producto eliminado del carrito.')
    return redirect('ver_carrito')

def ver_carrito(request):
    cart = request.session.get('cart', {})
    productos = []
    total = 0
    
    # Usar una copia de las claves del carrito para poder modificarlo mientras se itera
    cart_items = list(cart.items())
    
    for pid, cantidad in cart_items:
        try:
            producto = Producto.objects.get(id_producto=pid)
            subtotal = producto.precio_con_descuento() * cantidad
            productos.append({
                'producto': producto,
                'cantidad': cantidad,
                'subtotal': subtotal
            })
            total += subtotal
        except Producto.DoesNotExist:
            # Si el producto no existe, eliminarlo del carrito y continuar
            del cart[pid]
            request.session['cart'] = cart
            messages.warning(request, f'Un producto que tenías en el carrito ya no está disponible y ha sido eliminado.')

    # Nueva lógica para el botón de finalizar compra
    if request.method == 'POST':
        if not request.session.get('usuario_id'):
            messages.info(request, 'Por favor, inicia sesión para continuar con la compra.')
            return redirect(f"{reverse('login_compra')}?next={request.path}")
        else:
            return redirect('metodo_pago')

    context = {
        'productos': productos,
        'total': total
    }
    return render(request, 'Tienda/compra/carrito.html', context)

def contacto(request):
    """Vista para el formulario de contacto"""
    if request.method == 'POST':
        form = ContactoForm(request.POST)
        if form.is_valid():
            # Guardar el mensaje en la base de datos
            mensaje = form.save()
            
            # Enviar correo al administrador
            subject = f'Nuevo mensaje de contacto: {mensaje.asunto}'
            admin_message = render_to_string('Tienda/emails/contacto_admin.html', {
                'mensaje': mensaje,
            })
            send_mail(
                subject,
                admin_message,
                settings.EMAIL_HOST_USER,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            
            # Enviar confirmación al cliente
            client_subject = 'Hemos recibido tu mensaje - Calafate Austral'
            client_message = render_to_string('Tienda/emails/contacto_cliente.html', {
                'nombre': mensaje.nombre,
                'asunto': mensaje.asunto,
            })
            send_mail(
                client_subject,
                client_message,
                settings.EMAIL_HOST_USER,
                [mensaje.correo],
                fail_silently=False,
            )
            
            messages.success(request, 'Tu mensaje ha sido enviado exitosamente. Te hemos enviado una confirmación por correo.')
            return redirect('contacto')
    else:
        form = ContactoForm()
    
    context = {
        'form': form,
        'titulo': 'Contacto',
    }
    return render(request, 'Tienda/contacto.html', context)

def getnet_checkout(request):
    print("CHECKOUT SESSION key:", request.session.session_key)
    print("CHECKOUT SESSION dict:", dict(request.session))
    print("CHECKOUT metodo_pago:", request.session.get('metodo_pago'))
    """
    Crea una sesión de checkout con Getnet y redirige al usuario o responde con JSON para SPA
    """
    # Verificar que el usuario esté logueado
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'error': 'No autenticado'}, status=401)
        messages.error(request, 'Por favor inicie sesión para continuar')
        return redirect('login_compra')
    
    # Verificar que hay productos en el carrito
    cart = request.session.get('cart', {})
    if not cart:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'error': 'El carrito está vacío'}, status=400)
        messages.error(request, 'El carrito está vacío')
        return redirect('ver_carrito')

    # Obtener el método de pago de la sesión
    metodo_pago_id = request.session.get('metodo_pago')
    if not metodo_pago_id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'error': 'Seleccione un método de pago'}, status=400)
        messages.error(request, 'Por favor, seleccione un método de pago primero.')
        return redirect('metodo_pago')

    try:
        metodo_pago = MetodoPago.objects.get(id_metodo=metodo_pago_id)
        usuario = Usuario.objects.get(id=usuario_id)
        total = 0
        detalles = []
        for pid, cantidad in cart.items():
            producto = Producto.objects.get(id_producto=pid)
            precio_unitario = producto.precio_con_descuento()
            subtotal = precio_unitario * cantidad
            total += subtotal
            detalles.append({
                'producto': producto,
                'cantidad': cantidad,
                'precio_unitario': precio_unitario,
                'subtotal': subtotal
            })
        venta = Venta.objects.create(
            fecha_v=timezone.now(),
            total_v=total,
            tipo_comprador='usuario',
            usuario=usuario,
            estado_pago='pendiente',
            id_metodo=metodo_pago
        )
        for item in detalles:
            Detalleventa.objects.create(
                cantidad_dv=item['cantidad'],
                precio_unitario_dv=item['precio_unitario'],
                subtotal_dv=item['subtotal'],
                id_venta=venta,
                id_producto=item['producto']
            )
        getnet = GetnetIntegration()
        return_url = request.build_absolute_uri('/getnet/confirmation/')
        cancel_url = request.build_absolute_uri('/getnet/cancel/')
        checkout_data = getnet.create_checkout_session(venta, return_url, cancel_url)
        venta.checkout_session_id = checkout_data.get('session_id')
        venta.save()
        request.session['pending_venta_id'] = venta.id_venta
        checkout_url = checkout_data.get('checkout_url')
        if checkout_url:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({'checkout_url': checkout_url})
            else:
                return redirect(checkout_url)
        else:
            raise Exception("No se pudo obtener la URL de checkout")
    except MetodoPago.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'error': 'Método de pago inválido'}, status=400)
        messages.error(request, 'El método de pago seleccionado no es válido.')
        return redirect('metodo_pago')
    except Exception as e:
        logger.error(f"Error en checkout Getnet: {str(e)}")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'error': 'Error al procesar el pago. Por favor intente nuevamente.'}, status=500)
        messages.error(request, 'Error al procesar el pago. Por favor intente nuevamente.')
        return redirect('ver_carrito')

@csrf_exempt
@require_http_methods(["POST"])
def getnet_webhook(request):
    """
    Webhook para recibir notificaciones de Getnet sobre el estado del pago
    """
    try:
        # Obtener datos del webhook
        payload = json.loads(request.body)
        signature = request.headers.get('X-Getnet-Signature', '')
        
        # Inicializar integración
        getnet = GetnetIntegration()
        
        # Verificar firma del webhook
        if not getnet.verify_webhook(payload, signature):
            logger.warning("Webhook con firma inválida recibido")
            return HttpResponse(status=400)
        
        # Procesar webhook
        getnet.process_webhook(payload)
        
        logger.info(f"Webhook procesado exitosamente: {payload.get('order_id')}")
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}")
        return HttpResponse(status=500)

def getnet_confirmation(request):
    """
    Página de confirmación después del pago exitoso
    """
    venta_id = request.session.get('pending_venta_id')
    if not venta_id:
        messages.error(request, 'No se encontró información de la venta')
        return redirect('home')
    
    try:
        venta = Venta.objects.get(id_venta=venta_id)
        
        # Verificar estado del pago
        if venta.estado_pago == 'pagado':
            # Limpiar carrito
            request.session['cart'] = {}
            request.session.pop('pending_venta_id', None)
            
            # Obtener detalles de la venta
            detalles_venta = Detalleventa.objects.filter(id_venta=venta)
            
            context = {
                'venta': venta,
                'detalles_venta': detalles_venta,
                'success': True
            }
            return render(request, 'Tienda/compra/getnet_confirmation.html', context)
            
        elif venta.estado_pago == 'rechazado':
            messages.error(request, 'El pago fue rechazado. Por favor intente con otro método de pago.')
            return redirect('ver_carrito')
            
        else:
            # Pago aún pendiente, verificar estado
            getnet = GetnetIntegration()
            if venta.transaction_id:
                transaction_status = getnet.get_transaction_status(venta.transaction_id)
                # Actualizar estado según la respuesta
                # Implementar lógica adicional aquí
            
            messages.warning(request, 'El pago está siendo procesado. Recibirá una confirmación por email.')
            return redirect('home')
            
    except Venta.DoesNotExist:
        messages.error(request, 'Venta no encontrada')
        return redirect('home')
    except Exception as e:
        logger.error(f"Error en confirmación: {str(e)}")
        messages.error(request, 'Error al procesar la confirmación')
        return redirect('home')

def getnet_cancel(request):
    """
    Página cuando el usuario cancela el pago
    """
    venta_id = request.session.get('pending_venta_id')
    if venta_id:
        try:
            venta = Venta.objects.get(id_venta=venta_id)
            venta.estado_pago = 'cancelado'
            venta.save()
        except Venta.DoesNotExist:
            pass
    
    request.session.pop('pending_venta_id', None)
    messages.warning(request, 'El pago fue cancelado. Puede intentar nuevamente.')
    return redirect('ver_carrito')

def getnet_payment_status(request, venta_id):
    """
    Consulta el estado de un pago específico
    """
    try:
        venta = Venta.objects.get(id_venta=venta_id)
        
        if venta.transaction_id:
            getnet = GetnetIntegration()
            status_data = getnet.get_transaction_status(venta.transaction_id)
            return JsonResponse(status_data)
        else:
            return JsonResponse({'error': 'No hay transacción asociada'})
            
    except Venta.DoesNotExist:
        return JsonResponse({'error': 'Venta no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET", "POST"])
def set_payment_method(request):
    if request.method == "GET":
        return JsonResponse({
            "metodos": [
                {"id": 1, "nombre": "GetNet"}
            ]
        })
    try:
        data = json.loads(request.body)
        metodo = data.get('metodo')
        if metodo == 1:
            request.session['metodo_pago'] = 1
            request.session.modified = True
            request.session.save()
            print("Método de pago guardado en sesión:", request.session['metodo_pago'])
            print("Session key:", request.session.session_key)
            print("Session dict:", dict(request.session))
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Método de pago inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

@login_required
@user_passes_test(is_admin)
def admin_ofertas(request):
    ofertas = Oferta.objects.all().order_by('-id_oferta')
    if request.method == 'POST':
        form = OfertaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oferta creada exitosamente.')
            return redirect('admin_ofertas')
    else:
        form = OfertaForm()
    context = {
        'ofertas': ofertas,
        'form': form,
    }
    return render(request, 'Tienda/admin/ofertas.html', context)

@login_required
@user_passes_test(is_admin)
def admin_oferta_crear(request):
    if request.method == 'POST':
        form = OfertaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oferta creada exitosamente.')
            return redirect('admin_ofertas')
    else:
        form = OfertaForm()
    context = {
        'form': form,
        'titulo': 'Crear Oferta',
    }
    return render(request, 'Tienda/admin/oferta_form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_oferta_editar(request, oferta_id):
    oferta = get_object_or_404(Oferta, id_oferta=oferta_id)
    if request.method == 'POST':
        form = OfertaForm(request.POST, instance=oferta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oferta actualizada exitosamente.')
            return redirect('admin_ofertas')
    else:
        form = OfertaForm(instance=oferta)
    context = {
        'form': form,
        'oferta': oferta,
        'titulo': 'Editar Oferta',
    }
    return render(request, 'Tienda/admin/oferta_form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_oferta_eliminar(request, oferta_id):
    oferta = get_object_or_404(Oferta, id_oferta=oferta_id)
    if request.method == 'POST':
        oferta.delete()
        messages.success(request, 'Oferta eliminada exitosamente.')
        return redirect('admin_ofertas')
    context = {
        'oferta': oferta,
    }
    return render(request, 'Tienda/admin/oferta_confirmar_eliminar.html', context)

@login_required
@user_passes_test(is_admin)
def admin_mensajes(request):
    mensajes = Contacto.objects.all().order_by('-fecha')
    context = {'mensajes': mensajes}
    return render(request, 'Tienda/admin/mensajes.html', context)

@login_required
@user_passes_test(is_admin)
def admin_mensaje_detalle(request, mensaje_id):
    mensaje = get_object_or_404(Contacto, id_contacto=mensaje_id)
    context = {'mensaje': mensaje}
    return render(request, 'Tienda/admin/mensaje_detalle.html', context)

@login_required
@user_passes_test(is_admin)
def admin_mensaje_marcar_leido(request, mensaje_id):
    mensaje = get_object_or_404(Contacto, id_contacto=mensaje_id)
    mensaje.leido = True
    mensaje.save()
    messages.success(request, 'Mensaje marcado como leído.')
    return redirect('admin_mensajes')

@login_required
@user_passes_test(is_admin)
def admin_mensaje_marcar_no_leido(request, mensaje_id):
    mensaje = get_object_or_404(Contacto, id_contacto=mensaje_id)
    mensaje.leido = False
    mensaje.save()
    messages.success(request, 'Mensaje marcado como no leído.')
    return redirect('admin_mensajes')

@login_required
@user_passes_test(is_admin)
def admin_mensaje_eliminar(request, mensaje_id):
    mensaje = get_object_or_404(Contacto, id_contacto=mensaje_id)
    if request.method == 'POST':
        mensaje.delete()
        messages.success(request, 'Mensaje eliminado correctamente.')
        return redirect('admin_mensajes')
    context = {'mensaje': mensaje}
    return render(request, 'Tienda/admin/mensaje_confirmar_eliminar.html', context)

@login_required
@user_passes_test(is_admin)
def admin_usuarios(request):
    query = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')
    usuarios = Usuario.objects.all().order_by('-date_joined')
    if query:
        usuarios = usuarios.filter(
            Q(nombre_u__icontains=query) |
            Q(apellido_u__icontains=query) |
            Q(correo_u__icontains=query)
        )
    if tipo:
        usuarios = usuarios.filter(tipo_u=tipo)
    paginator = Paginator(usuarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj, 'query': query, 'tipo': tipo}
    return render(request, 'Tienda/admin/usuarios.html', context)

@login_required
@user_passes_test(is_admin)
def admin_usuario_crear(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.set_password(form.cleaned_data['contrasena'])
            usuario.save()
            messages.success(request, 'Usuario creado exitosamente.')
            return redirect('admin_usuarios')
    else:
        form = UsuarioForm()
    context = {'form': form, 'titulo': 'Crear Usuario'}
    return render(request, 'Tienda/admin/usuario_form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_usuario_editar(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save(commit=False)
            if form.cleaned_data['contrasena']:
                usuario.set_password(form.cleaned_data['contrasena'])
            usuario.save()
            messages.success(request, 'Usuario actualizado exitosamente.')
            return redirect('admin_usuarios')
    else:
        form = UsuarioForm(instance=usuario)
    context = {'form': form, 'titulo': 'Editar Usuario'}
    return render(request, 'Tienda/admin/usuario_form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_usuario_eliminar(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, 'Usuario eliminado correctamente.')
        return redirect('admin_usuarios')
    context = {'usuario': usuario}
    return render(request, 'Tienda/admin/usuario_confirmar_eliminar.html', context)

@login_required
@user_passes_test(is_admin)
def admin_configuracion(request):
    config = ConfiguracionTienda.get_solo()
    if request.method == 'POST':
        form = ConfiguracionTiendaForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración actualizada correctamente.')
            return redirect('admin_configuracion')
    else:
        form = ConfiguracionTiendaForm(instance=config)
    context = {'form': form, 'config': config}
    return render(request, 'Tienda/admin/configuracion.html', context)
