from django.core.management.base import BaseCommand

from reservas.models import Equipo

# (prefijo, cantidad, nombre, categoría, ubicación, imagen en media/equipos/)
LOTES = [
    ("CAM", 5, "Cámara Sony 4K", "Video", "Sala de Grabación", "equipos/camara.jpg"),
    ("PROY", 10, "Proyector Epson PowerLite", "Proyección", "Sala de Proyección", "equipos/proyector.jpg"),
    ("LAP", 25, "Laptop HP 14", "Computación", "Bodega de Computación", "equipos/laptop.jpg"),
]


class Command(BaseCommand):
    help = "Carga los equipos iniciales (5 cámaras, 10 proyectores, 25 laptops). Se puede ejecutar varias veces."

    def handle(self, *args, **options):
        creados = actualizados = 0
        for prefijo, cantidad, nombre, categoria, ubicacion, imagen in LOTES:
            for n in range(1, cantidad + 1):
                _, nuevo = Equipo.objects.update_or_create(
                    codigo=f"{prefijo}-{n:03d}",
                    defaults={"nombre": nombre, "categoria": categoria,
                              "ubicacion": ubicacion, "imagen": imagen, "activo": True},
                )
                creados += nuevo
                actualizados += not nuevo
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {creados} equipos creados, {actualizados} actualizados (total {Equipo.objects.count()})."))
