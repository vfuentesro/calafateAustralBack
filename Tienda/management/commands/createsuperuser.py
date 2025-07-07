from django.contrib.auth.management.commands.createsuperuser import Command as BaseCreateSuperuserCommand
from django.core.management.base import CommandError
from Tienda.models import Usuario

class Command(BaseCreateSuperuserCommand):
    help = 'Crea un superusuario pidiendo el RUT completo (ej: 12345678-9)'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--rut', dest='rut', type=str, help='RUT completo (ej: 12345678-9)')

    def handle(self, *args, **options):
        rut = options.get('rut')
        if not rut:
            rut = input('RUT completo (ej: 12345678-9): ')
        options['rut'] = rut
        # Elimina los campos separados si están presentes
        options.pop('rut_numero', None)
        options.pop('rut_dv', None)
        super().handle(*args, **options) 