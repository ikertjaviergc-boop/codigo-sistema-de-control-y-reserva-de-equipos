from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

BLOQUES = [
    (1, "Bloque 1: 08:30 - 10:00 hrs"),
    (2, "Bloque 2: 10:15 - 11:45 hrs"),
    (3, "Bloque 3: 12:00 - 13:30 hrs"),
    (4, "Bloque 4: 14:30 - 16:00 hrs"),
    (5, "Bloque 5: 16:15 - 17:45 hrs"),
]
INICIO_BLOQUE = {1: "08:30", 2: "10:15", 3: "12:00", 4: "14:30", 5: "16:15"}
FIN_BLOQUE = {1: "10:00", 2: "11:45", 3: "13:30", 4: "16:00", 5: "17:45"}


class Perfil(models.Model):
    TIPOS = [("Docente", "Docente"), ("Estudiante", "Estudiante")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    tipo = models.CharField(max_length=20, choices=TIPOS, default="Docente")
    departamento = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.tipo})"


class Equipo(models.Model):
    CATEGORIAS = [
        ("Proyección", "Proyección"),
        ("Video", "Video"),
        ("Computación", "Computación"),
        ("Fotografía", "Fotografía"),
        ("Audio", "Audio"),
        ("Otros", "Otros"),
    ]
    nombre = models.CharField(max_length=100)
    codigo = models.CharField("código interno", max_length=20, unique=True)
    categoria = models.CharField(max_length=30, choices=CATEGORIAS, default="Otros")
    ubicacion = models.CharField("ubicación", max_length=100, blank=True)
    imagen = models.ImageField(upload_to="equipos/", blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Reserva(models.Model):
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    ESTADOS = [(CONFIRMADA, "Confirmada"), (CANCELADA, "Cancelada")]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservas")
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="reservas")
    fecha = models.DateField("fecha de uso")
    bloque = models.PositiveSmallIntegerField("bloque horario", choices=BLOQUES)
    estado = models.CharField(max_length=12, choices=ESTADOS, default=CONFIRMADA)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "bloque"]

    def __str__(self):
        return f"{self.codigo} - {self.equipo}"

    @property
    def codigo(self):
        return f"#RES-{self.pk}" if self.pk else "#RES-(nueva)"

    @property
    def horario(self):
        return f"{INICIO_BLOQUE[self.bloque]} - {FIN_BLOQUE[self.bloque]} hrs"

    @property
    def limite_retiro(self):
        inicio = datetime.strptime(INICIO_BLOQUE[self.bloque], "%H:%M")
        return (inicio + timedelta(minutes=15)).strftime("%H:%M")

    def clean(self):
        # Evita solapamientos: un equipo, un bloque, una fecha
        if self.estado == self.CONFIRMADA and self.equipo_id and self.fecha and self.bloque:
            choque = Reserva.objects.filter(
                equipo_id=self.equipo_id, fecha=self.fecha,
                bloque=self.bloque, estado=self.CONFIRMADA,
            ).exclude(pk=self.pk)
            if choque.exists():
                raise ValidationError("El equipo ya está reservado en esa fecha y bloque horario.")
