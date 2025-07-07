#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Backedn_Calafate_Austral.settings')
django.setup()

from Tienda.models import Producto, Categoria, Oferta

def test_bulk_edit():
    print("=== PRUEBA DE EDICIÓN MASIVA ===")
    
    # Verificar productos existentes
    productos = Producto.objects.all()
    print(f"Productos existentes: {productos.count()}")
    
    for producto in productos[:3]:  # Mostrar solo los primeros 3
        print(f"- {producto.nombre_p} (ID: {producto.id_producto})")
        print(f"  Precio: ${producto.precio_p}")
        print(f"  Stock: {producto.stock_p}")
        print(f"  Categoría: {producto.id_categoria}")
        print(f"  Oferta: {producto.id_oferta}")
        print()
    
    # Verificar categorías
    categorias = Categoria.objects.all()
    print(f"Categorías disponibles: {categorias.count()}")
    for cat in categorias:
        print(f"- {cat.nombre_c} (ID: {cat.id_categoria})")
    
    # Verificar ofertas
    ofertas = Oferta.objects.all()
    print(f"Ofertas disponibles: {ofertas.count()}")
    for oferta in ofertas:
        print(f"- {oferta.descuento}% - {oferta.estado} (ID: {oferta.id_oferta})")
    
    print("\n=== FIN DE PRUEBA ===")

if __name__ == "__main__":
    test_bulk_edit() 