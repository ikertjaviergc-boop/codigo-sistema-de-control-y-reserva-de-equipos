from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("registro/", views.registro, name="registro"),
    path("salir/", LogoutView.as_view(), name="salir"),
    path("catalogo/", views.catalogo, name="catalogo"),
    path("reservar/<int:equipo_id>/", views.reservar, name="reservar"),
    path("solicitar/", views.solicitar_lote, name="solicitar_lote"),
    path("reservas/lote/", views.reserva_lote, name="reserva_lote"),
    path("reservas/", views.reservas, name="reservas"),
    path("reservas/nueva/", views.reserva_crear, name="reserva_crear"),
    path("reservas/<int:pk>/", views.reserva_detalle, name="reserva_detalle"),
    path("reservas/<int:pk>/cancelar/", views.reserva_cancelar, name="reserva_cancelar"),
    path("reservas/<int:pk>/editar/", views.reserva_editar, name="reserva_editar"),
    path("reservas/<int:pk>/eliminar/", views.reserva_eliminar, name="reserva_eliminar"),
    path("equipos/", views.equipos, name="equipos"),
    path("usuarios/", views.usuarios, name="usuarios"),
]
