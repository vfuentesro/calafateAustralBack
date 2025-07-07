from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html
from django.utils import timezone
from django.db import transaction
from .models import Usuario, MetodoPago, Categoria, Oferta, Producto, Venta, Detalleventa, DireccionUsuario, ImagenProducto, Contacto
from .servicios_envio import actualizar_estado_envio
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .forms import CustomSuperuserCreationForm

# Acciones personalizadas
def modificar_datos_productos(modeladmin, request, queryset):
    if 'apply' in request.POST:
        count = 0
        errors = []
        
        for producto in queryset:
            try:
                # Actualizar campos si se proporcionaron
                if request.POST.get('sku') and request.POST.get('sku').strip():
                    producto.sku = request.POST.get('sku').strip()

                if request.POST.get('nombre_p') and request.POST.get('nombre_p').strip():
                    producto.nombre_p = request.POST.get('nombre_p').strip()
                
                if request.POST.get('descripcion_p') and request.POST.get('descripcion_p').strip():
                    producto.descripcion_p = request.POST.get('descripcion_p').strip()
                
                if request.POST.get('precio_p') and request.POST.get('precio_p').strip():
                    try:
                        precio = int(request.POST.get('precio_p').strip())
                        if precio >= 0:
                            producto.precio_p = precio
                        else:
                            errors.append(f"Precio inválido para {producto.nombre_p}: {request.POST.get('precio_p')}")
                            continue
                    except ValueError:
                        errors.append(f"Precio inválido para {producto.nombre_p}: {request.POST.get('precio_p')}")
                        continue
                
                if request.POST.get('stock_p') and request.POST.get('stock_p').strip():
                    try:
                        stock = int(request.POST.get('stock_p').strip())
                        if stock >= 0:
                            producto.stock_p = stock
                        else:
                            errors.append(f"Stock inválido para {producto.nombre_p}: {request.POST.get('stock_p')}")
                            continue
                    except ValueError:
                        errors.append(f"Stock inválido para {producto.nombre_p}: {request.POST.get('stock_p')}")
                        continue
                
                # Manejar categoría
                categoria_id = request.POST.get('id_categoria')
                if categoria_id is not None:  # Incluye '0' y ''
                    if categoria_id == '0':
                        # No cambiar la categoría
                        pass
                    elif categoria_id == '':
                        # Quitar categoría
                        producto.id_categoria = None
                    else:
                        # Asignar nueva categoría
                        try:
                            categoria = Categoria.objects.get(id_categoria=categoria_id)
                            producto.id_categoria = categoria
                        except Categoria.DoesNotExist:
                            errors.append(f"Categoría no encontrada para {producto.nombre_p}: {categoria_id}")
                            continue
                
                # Manejar oferta
                oferta_id = request.POST.get('id_oferta')
                if oferta_id is not None:  # Incluye '0' y ''
                    if oferta_id == '0':
                        # No cambiar la oferta
                        pass
                    elif oferta_id == '':
                        # Quitar oferta
                        producto.id_oferta = None
                    else:
                        # Asignar nueva oferta
                        try:
                            oferta = Oferta.objects.get(id_oferta=oferta_id)
                            producto.id_oferta = oferta
                        except Oferta.DoesNotExist:
                            errors.append(f"Oferta no encontrada para {producto.nombre_p}: {oferta_id}")
                            continue
                
                producto.save()
                count += 1
                
            except Exception as e:
                errors.append(f"Error al modificar {producto.nombre_p}: {str(e)}")
                continue
        
        # Mostrar mensajes
        if count > 0:
            messages.success(request, f'Se modificaron {count} productos exitosamente.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        
        return redirect('admin:Tienda_producto_changelist')
    
    # Mostrar formulario de edición masiva
    categorias = Categoria.objects.all()
    ofertas = Oferta.objects.all()
    context = {
        'title': 'Modificar productos seleccionados',
        'queryset': queryset,
        'categorias': categorias,
        'ofertas': ofertas,
        'opts': modeladmin.model._meta,
    }
    return render(request, 'admin/Tienda/producto/bulk_edit.html', context)

modificar_datos_productos.short_description = "Modificar datos de productos seleccionados"

class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 1
    fields = ('imagen', 'descripcion', 'orden')

@admin.register(ImagenProducto)
class ImagenProductoAdmin(admin.ModelAdmin):
    list_display = ('id_imagen', 'producto', 'imagen_miniatura', 'descripcion', 'orden', 'fecha_subida')
    list_filter = ('producto', 'fecha_subida')
    search_fields = ('producto__nombre_p', 'descripcion')
    ordering = ['producto', 'orden', 'fecha_subida']

    def imagen_miniatura(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" height="50"/>', obj.imagen.url)
        return "Sin imagen"
    imagen_miniatura.short_description = 'Vista previa'

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    add_form = CustomSuperuserCreationForm
    list_display = ('rut_usuario', 'nombre_u', 'apellido_u', 'correo_u', 'numero_telefono_u', 'tipo_u')
    search_fields = ('nombre_u', 'apellido_u', 'correo_u', 'rut_numero', 'rut_dv', 'numero_telefono_u')
    list_filter = ('tipo_u',)
    ordering = ('correo_u',)

    fieldsets = (
        (None, {
            'fields': ('rut', 'nombre_u', 'apellido_u', 'correo_u', 'numero_telefono_u', 'tipo_u', 'password')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Fechas importantes', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('rut', 'nombre_u', 'apellido_u', 'correo_u', 'numero_telefono_u', 'tipo_u', 'password1', 'password2'),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['rut'] = forms.CharField(label='RUT', help_text='Ingrese el RUT completo (ej: 12345678-9)')
        return form

    def delete_model(self, request, obj):
        from .models import Venta
        if Venta.objects.filter(rut_usuario=obj).exists():
            self.message_user(
                request,
                "No se puede eliminar el usuario porque existen ventas asociadas a este RUT.",
                level=messages.ERROR
            )
        else:
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        from .models import Venta
        for obj in queryset:
            if Venta.objects.filter(rut_usuario=obj).exists():
                self.message_user(
                    request,
                    f"No se puede eliminar el usuario '{obj.rut_usuario}' porque existen ventas asociadas a este RUT.",
                    level=messages.ERROR
                )
            else:
                obj.delete()

@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('id_metodo', 'nombre', 'descripcion')
    search_fields = ('nombre',)

    def delete_model(self, request, obj):
        from .models import Venta
        if Venta.objects.filter(id_metodo=obj).exists():
            self.message_user(
                request,
                "No se puede eliminar el método de pago porque existen ventas asociadas.",
                level=messages.ERROR
            )
        else:
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        from .models import Venta
        for obj in queryset:
            if Venta.objects.filter(id_metodo=obj).exists():
                self.message_user(
                    request,
                    f"No se puede eliminar el método de pago '{obj.nombre}' porque existen ventas asociadas.",
                    level=messages.ERROR
                )
            else:
                obj.delete()

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id_categoria', 'nombre_c')
    search_fields = ('nombre_c',)

    def delete_model(self, request, obj):
        if Producto.objects.filter(id_categoria=obj).exists():
            self.message_user(
                request,
                "No se puede eliminar la categoría porque existen productos asociados.",
                level=messages.ERROR
            )
        else:
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if Producto.objects.filter(id_categoria=obj).exists():
                self.message_user(
                    request,
                    f"No se puede eliminar la categoría '{obj.nombre_c}' porque existen productos asociados.",
                    level=messages.ERROR
                )
            else:
                obj.delete()

@admin.register(Oferta)
class OfertaAdmin(admin.ModelAdmin):
    list_display = ('id_oferta', 'descuento_porcentaje', 'fecha_inicio', 'fecha_fin', 'estado')
    list_filter = ('estado', 'fecha_inicio', 'fecha_fin')
    search_fields = ('estado',)

    def descuento_porcentaje(self, obj):
        return f"{obj.descuento}%"
    descuento_porcentaje.short_description = 'Descuento'

    def delete_model(self, request, obj):
        from .models import Producto
        if Producto.objects.filter(id_oferta=obj).exists():
            self.message_user(
                request,
                "No se puede eliminar la oferta porque existen productos asociados.",
                level=messages.ERROR
            )
        else:
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        from .models import Producto
        for obj in queryset:
            if Producto.objects.filter(id_oferta=obj).exists():
                self.message_user(
                    request,
                    f"No se puede eliminar la oferta con ID '{obj.id_oferta}' porque existen productos asociados.",
                    level=messages.ERROR
                )
            else:
                obj.delete()

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id_producto', 'sku', 'nombre_p', 'precio_p_formateado', 'stock_p', 'get_id_categoria', 'imagen_miniatura')
    list_filter = ('id_categoria', 'id_oferta')
    search_fields = ('nombre_p', 'descripcion_p', 'sku')
    actions = [modificar_datos_productos]
    inlines = [ImagenProductoInline]
    
    fieldsets = (
        (None, {
            'fields': ('sku', 'nombre_p', 'descripcion_p')
        }),
        ('Detalles de Precio y Stock', {
            'fields': ('precio_p', 'stock_p')
        }),
        ('Dimensiones para Envío (en cm y kg)', {
            'fields': ('peso_kg', 'alto_cm', 'ancho_cm', 'largo_cm'),
            'classes': ('collapse',),
            'description': 'Estos valores son cruciales para cotizar los envíos.'
        }),
        ('Clasificación', {
            'fields': ('id_categoria', 'id_oferta')
        }),
        ('Imagen Principal', {
            'fields': ('imagen',)
        }),
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in ['stock_p', 'precio_p', 'peso_kg', 'alto_cm', 'ancho_cm', 'largo_cm']:
            kwargs['widget'] = forms.NumberInput(attrs={'min': '0'})
        return super().formfield_for_dbfield(db_field, **kwargs)

    def precio_p_formateado(self, obj):
        return f"${obj.precio_p:,.0f}".replace(",", ".")
    precio_p_formateado.short_description = 'Precio'
    
    def get_id_categoria(self, obj):
        if obj.id_categoria:
            return f"{obj.id_categoria.nombre_c}"
        return "Sin categoría"
    get_id_categoria.short_description = 'Categoría'
    
    def get_id_oferta(self, obj):
        if obj.id_oferta:
            return f"{obj.id_oferta.descuento}% - {obj.id_oferta.estado}"
        return "Sin oferta"
    get_id_oferta.short_description = 'Oferta'

    def imagen_miniatura(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.imagen.url)
        return "Sin imagen"
    imagen_miniatura.short_description = 'Imagen'

    def delete_model(self, request, obj):
        from .models import Detalleventa
        if Detalleventa.objects.filter(id_producto=obj).exists():
            self.message_user(
                request,
                "No se puede eliminar el producto porque existen detalles de venta asociados.",
                level=messages.ERROR
            )
        else:
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        from .models import Detalleventa
        for obj in queryset:
            if Detalleventa.objects.filter(id_producto=obj).exists():
                self.message_user(
                    request,
                    f"No se puede eliminar el producto '{obj.nombre_p}' porque existen detalles de venta asociados.",
                    level=messages.ERROR
                )
            else:
                obj.delete()

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id_venta', 'fecha_v', 'usuario', 'total_v', 'id_metodo', 'estado_pago')
    list_filter = ('estado_pago', 'id_metodo', 'fecha_v')
    search_fields = ('id_venta', 'usuario__rut_usuario', 'usuario__nombre_u')
    readonly_fields = ('id_venta',)
    actions = ['marcar_como_pagado', 'marcar_como_rechazado']

    def marcar_como_pagado(self, request, queryset):
        """
        Marca las ventas como pagadas y descuenta el stock de los productos.
        Solo procesa ventas que no estén ya pagadas.
        """
        updated_count = 0
        skipped_count = 0
        error_list = []

        for venta in queryset:
            if venta.estado_pago == 'pagado':
                skipped_count += 1
                continue
            
            try:
                with transaction.atomic():
                    # Obtenemos los detalles y bloqueamos los productos correspondientes para la actualización.
                    detalles = Detalleventa.objects.filter(id_venta=venta).select_related('id_producto')
                    product_ids = [d.id_producto.id_producto for d in detalles]
                    productos = Producto.objects.select_for_update().filter(id_producto__in=product_ids)
                    
                    # Convertimos a dict para fácil acceso
                    productos_dict = {p.id_producto: p for p in productos}

                    # Verificamos y actualizamos el stock
                    for detalle in detalles:
                        producto = productos_dict.get(detalle.id_producto.id_producto)
                        if producto.stock_p < detalle.cantidad_dv:
                            raise Exception(f"Stock insuficiente para '{producto.nombre_p}' en la venta #{venta.id_venta}.")
                        
                        producto.stock_p -= detalle.cantidad_dv
                    
                    # Guardamos todos los productos actualizados
                    for producto in productos_dict.values():
                        producto.save(update_fields=['stock_p'])

                    # Finalmente, actualizamos la venta
                    venta.estado_pago = 'pagado'
                    venta.fecha_pago = timezone.now()
                    venta.save(update_fields=['estado_pago', 'fecha_pago'])
                    
                    updated_count += 1

            except Exception as e:
                error_list.append(str(e))

        if updated_count > 0:
            self.message_user(request, f"{updated_count} ventas marcadas como pagadas y su stock ha sido descontado.", messages.SUCCESS)
        if skipped_count > 0:
            self.message_user(request, f"{skipped_count} ventas ya estaban pagadas y fueron omitidas.", messages.WARNING)
        if error_list:
            for error in error_list:
                self.message_user(request, f"Error: {error}", messages.ERROR)

    marcar_como_pagado.short_description = "Marcar como pagado (y descontar stock)"

    def marcar_como_rechazado(self, request, queryset):
        updated = queryset.update(estado_pago='rechazado')
        self.message_user(request, f"{updated} ventas marcadas como rechazadas.")
    marcar_como_rechazado.short_description = "Marcar como rechazado"

    fieldsets = (
        ('Información Básica', {
            'fields': ('id_venta', 'fecha_v', 'total_v', 'tipo_comprador', 'usuario', 'id_metodo')
        }),
        ('Estado del Pago', {
            'fields': ('estado_pago', 'transaction_id', 'fecha_pago', 'checkout_session_id')
        }),
        ('Datos Adicionales', {
            'fields': ('webhook_data',),
            'classes': ('collapse',)
        }),
    )

    def total_v_formateado(self, obj):
        return f"${obj.total_v:,.0f}".replace(",", ".")
    total_v_formateado.short_description = 'Total Venta'

@admin.register(Detalleventa)
class DetalleventaAdmin(admin.ModelAdmin):
    list_display = ('id_detalleventa', 'get_id_venta', 'get_producto_sku', 'get_id_producto', 'cantidad_dv', 'estado', 'numero_seguimiento')
    list_filter = ('estado', 'id_venta', 'id_producto')
    search_fields = ('id_venta__rut_usuario__nombre_u', 'id_producto__nombre_p', 'numero_seguimiento', 'id_producto__sku')
    list_editable = ('estado', 'numero_seguimiento')
    actions = ['actualizar_estado_envio_action']

    def precio_unitario_formateado(self, obj):
        return f"${obj.precio_unitario_dv:,.0f}"
    precio_unitario_formateado.short_description = 'Precio Unitario'

    def subtotal_formateado(self, obj):
        return f"${obj.subtotal_dv:,.0f}"
    subtotal_formateado.short_description = 'Subtotal'

    def get_producto_sku(self, obj):
        return obj.id_producto.sku if obj.id_producto else '-'
    get_producto_sku.short_description = 'SKU Producto'

    def get_id_producto(self, obj):
        return obj.id_producto.nombre_p if obj.id_producto else '-'
    get_id_producto.short_description = 'Producto'

    def get_id_venta(self, obj):
        return f"Venta #{obj.id_venta.id_venta}" if obj.id_venta else '-'
    get_id_venta.short_description = 'Venta'

    def actualizar_estado_envio_action(self, request, queryset):
        for detalle in queryset:
            actualizar_estado_envio(detalle)
    actualizar_estado_envio_action.short_description = "Actualizar estado de envío"

@admin.register(DireccionUsuario)
class DireccionUsuarioAdmin(admin.ModelAdmin):
    list_display = ('id_direccion_usuario', 'usuario', 'region', 'comuna', 'calle', 'numero', 'numero_departamento_oficina_otro', 'nombre_receptor', 'telefono_receptor')
    search_fields = ('usuario__rut_usuario', 'region', 'comuna', 'calle', 'nombre_receptor', 'telefono_receptor')
    list_filter = ('region', 'comuna')
    verbose_name_plural = 'Direcciones de Envío'

@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ('id_contacto', 'nombre', 'correo', 'asunto', 'fecha', 'leido')
    list_filter = ('leido', 'fecha')
    search_fields = ('nombre', 'correo', 'asunto', 'mensaje')
    readonly_fields = ('id_contacto', 'fecha')
    list_editable = ('leido',)
    ordering = ['-fecha']
    
    fieldsets = (
        ('Información del Contacto', {
            'fields': ('nombre', 'correo', 'asunto')
        }),
        ('Mensaje', {
            'fields': ('mensaje',)
        }),
        ('Estado', {
            'fields': ('leido', 'fecha')
        }),
    )
    
    actions = ['marcar_como_leido', 'marcar_como_no_leido']
    
    def marcar_como_leido(self, request, queryset):
        updated = queryset.update(leido=True)
        self.message_user(request, f"{updated} mensajes marcados como leídos.")
    marcar_como_leido.short_description = "Marcar como leído"
    
    def marcar_como_no_leido(self, request, queryset):
        updated = queryset.update(leido=False)
        self.message_user(request, f"{updated} mensajes marcados como no leídos.")
    marcar_como_no_leido.short_description = "Marcar como no leído"
