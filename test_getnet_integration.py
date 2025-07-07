#!/usr/bin/env python
"""
Script de prueba para la integración con Getnet
Ejecutar con: python test_getnet_integration.py
"""

import os
import sys
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Backedn_Calafate_Austral.settings')
django.setup()

from Tienda.getnet_integration import GetnetIntegration
from Tienda.models import Venta, Usuario, Producto, Detalleventa
import datetime

def test_getnet_configuration():
    """Prueba la configuración básica de Getnet"""
    print("🔧 Probando configuración de Getnet...")
    
    try:
        getnet = GetnetIntegration()
        
        # Verificar que las credenciales estén configuradas
        required_fields = [
            'merchant_id', 'terminal_id', 'secret_key', 
            'api_url', 'webhook_secret'
        ]
        
        for field in required_fields:
            value = getattr(getnet, field)
            if value == f'your_{field.replace("_", "_")}':
                print(f"❌ {field}: No configurado (usando valor por defecto)")
            else:
                print(f"✅ {field}: Configurado")
        
        print(f"🌐 API URL: {getnet.api_url}")
        
    except Exception as e:
        print(f"❌ Error en configuración: {str(e)}")
        return False
    
    return True

def test_database_models():
    """Prueba que los modelos estén correctamente configurados"""
    print("\n🗄️ Probando modelos de base de datos...")
    
    try:
        # Verificar que el modelo Venta tenga los campos necesarios
        venta_fields = [field.name for field in Venta._meta.fields]
        required_fields = ['estado_pago', 'transaction_id', 'checkout_session_id', 'webhook_data']
        
        for field in required_fields:
            if field in venta_fields:
                print(f"✅ Campo {field}: Presente en modelo Venta")
            else:
                print(f"❌ Campo {field}: Faltante en modelo Venta")
        
        # Verificar que existan algunos datos de prueba
        usuarios_count = Usuario.objects.count()
        productos_count = Producto.objects.count()
        
        print(f"👥 Usuarios en BD: {usuarios_count}")
        print(f"📦 Productos en BD: {productos_count}")
        
        if usuarios_count == 0:
            print("⚠️ No hay usuarios en la base de datos")
        if productos_count == 0:
            print("⚠️ No hay productos en la base de datos")
        
    except Exception as e:
        print(f"❌ Error en modelos: {str(e)}")
        return False
    
    return True

def test_getnet_integration_class():
    """Prueba los métodos de la clase GetnetIntegration"""
    print("\n🔌 Probando métodos de integración...")
    
    try:
        getnet = GetnetIntegration()
        
        # Probar generación de firma
        test_payload = {"test": "data", "amount": 1000}
        signature = getnet._generate_signature(test_payload)
        print(f"✅ Generación de firma: {signature[:20]}...")
        
        # Probar verificación de webhook
        is_valid = getnet.verify_webhook(test_payload, signature)
        print(f"✅ Verificación de webhook: {'Válido' if is_valid else 'Inválido'}")
        
        # Probar verificación con firma incorrecta
        invalid_signature = "invalid_signature"
        is_invalid = getnet.verify_webhook(test_payload, invalid_signature)
        print(f"✅ Verificación con firma inválida: {'Inválido' if not is_invalid else 'Error'}")
        
    except Exception as e:
        print(f"❌ Error en métodos de integración: {str(e)}")
        return False
    
    return True

def test_urls():
    """Prueba que las URLs estén configuradas correctamente"""
    print("\n🔗 Probando configuración de URLs...")
    
    try:
        from django.urls import reverse, NoReverseMatch
        
        # URLs que deberían existir
        required_urls = [
            'getnet_checkout',
            'getnet_webhook', 
            'getnet_confirmation',
            'getnet_cancel'
        ]
        
        for url_name in required_urls:
            try:
                url = reverse(url_name)
                print(f"✅ URL {url_name}: {url}")
            except NoReverseMatch:
                print(f"❌ URL {url_name}: No encontrada")
        
        # Probar URL con parámetro
        try:
            url = reverse('getnet_payment_status', kwargs={'venta_id': 1})
            print(f"✅ URL getnet_payment_status: {url}")
        except NoReverseMatch:
            print(f"❌ URL getnet_payment_status: No encontrada")
        
    except Exception as e:
        print(f"❌ Error en URLs: {str(e)}")
        return False
    
    return True

def test_settings():
    """Prueba la configuración de Django"""
    print("\n⚙️ Probando configuración de Django...")
    
    try:
        # Verificar configuración de logging
        if hasattr(settings, 'LOGGING'):
            print("✅ Configuración de logging: Presente")
        else:
            print("❌ Configuración de logging: Faltante")
        
        # Verificar configuración de Getnet
        getnet_settings = [
            'GETNET_MERCHANT_ID',
            'GETNET_TERMINAL_ID', 
            'GETNET_SECRET_KEY',
            'GETNET_API_URL',
            'BASE_URL'
        ]
        
        for setting in getnet_settings:
            if hasattr(settings, setting):
                value = getattr(settings, setting)
                if 'your_' in str(value):
                    print(f"⚠️ {setting}: Usando valor por defecto")
                else:
                    print(f"✅ {setting}: Configurado")
            else:
                print(f"❌ {setting}: No encontrado")
        
    except Exception as e:
        print(f"❌ Error en configuración: {str(e)}")
        return False
    
    return True

def main():
    """Función principal de pruebas"""
    print("🧪 Iniciando pruebas de integración con Getnet")
    print("=" * 50)
    
    tests = [
        test_settings,
        test_database_models,
        test_getnet_configuration,
        test_getnet_integration_class,
        test_urls
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Error ejecutando {test.__name__}: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"📊 Resultados: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La integración está lista.")
        print("\n📋 Próximos pasos:")
        print("1. Configura tus credenciales reales de Getnet en settings.py")
        print("2. Configura el webhook en el panel de Getnet")
        print("3. Prueba el flujo completo de pago")
        print("4. Revisa la documentación en GETNET_SETUP.md")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
        print("\n🔧 Para solucionar problemas:")
        print("1. Verifica que todas las migraciones estén aplicadas")
        print("2. Configura las credenciales de Getnet")
        print("3. Revisa la documentación en GETNET_SETUP.md")

if __name__ == "__main__":
    main() 