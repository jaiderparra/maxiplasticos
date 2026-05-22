import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Crea el superusuario admin desde variables de entorno si no existe'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        email    = os.environ.get('ADMIN_EMAIL', 'maxiplasticos60@gmail.com')
        password = os.environ.get('ADMIN_PASSWORD', '')

        if not password:
            self.stdout.write(self.style.WARNING(
                'ADMIN_PASSWORD no configurada — saltando creación de admin.'
            ))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(
                f'Admin "{username}" ya existe — no se modifica.'
            ))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(
            f'Superusuario "{username}" creado correctamente.'
        ))
