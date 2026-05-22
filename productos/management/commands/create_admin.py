import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Crea o actualiza el superusuario admin desde variables de entorno'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        email    = os.environ.get('ADMIN_EMAIL', 'maxiplasticos60@gmail.com')
        password = os.environ.get('ADMIN_PASSWORD', '')

        if not password:
            self.stdout.write(self.style.WARNING(
                'ADMIN_PASSWORD no configurada — saltando.'
            ))
            return

        user, created = User.objects.get_or_create(username=username)
        user.email        = email
        user.is_staff     = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        accion = 'creado' if created else 'actualizado'
        self.stdout.write(self.style.SUCCESS(
            f'Superusuario "{username}" {accion} correctamente.'
        ))
