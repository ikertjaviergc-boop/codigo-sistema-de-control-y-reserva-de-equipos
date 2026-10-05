from django.contrib import admin

from .models import Equipo, Perfil, Reserva

admin.site.register(Perfil)


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "categoria", "ubicacion", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("nombre", "codigo")


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("id", "equipo", "usuario", "fecha", "bloque", "estado")
    list_filter = ("estado", "fecha")
