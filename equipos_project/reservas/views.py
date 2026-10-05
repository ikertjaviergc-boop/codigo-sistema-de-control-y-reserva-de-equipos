from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import urlencode
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import RegistroForm, ReservaAdminForm, ReservaForm
from .models import BLOQUES, Equipo, Reserva


def solo_admin(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return vista(request, *args, **kwargs)
    return login_required(envoltura)


def qr_svg(texto):
    try:
        import qrcode
        import qrcode.image.svg
        img = qrcode.make(texto, image_factory=qrcode.image.svg.SvgPathImage, box_size=10)
        return img.to_string(encoding="unicode")
    except Exception:
        return None


# ---------- Inicio, registro y sesión ----------

def inicio(request):
    if request.user.is_authenticated:
        qs = Reserva.objects.all() if request.user.is_superuser else Reserva.objects.filter(usuario=request.user)
        activas = qs.filter(estado=Reserva.CONFIRMADA)
        return render(request, "inicio.html", {
            "total_activas": activas.count(),
            "proximas": activas.filter(fecha__gte=timezone.localdate()).select_related("equipo", "usuario").order_by("fecha", "bloque")[:5],
            "total_equipos": Equipo.objects.filter(activo=True).count(),
        })

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        if not request.POST.get("recordar"):
            request.session.set_expiry(0)  # cookie de sesión: se borra al cerrar el navegador
        destino = request.GET.get("next", "")
        if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
            return redirect(destino)
        return redirect("inicio")
    return render(request, "inicio.html", {"form": form})


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Tu cuenta fue creada. Ya puedes solicitar equipos.")
        return redirect("catalogo")
    return render(request, "registro.html", {"form": form})


# ---------- Catálogo y solicitudes ----------

@login_required
def catalogo(request):
    fecha = parse_date(request.GET.get("fecha", "")) or timezone.localdate()
    try:
        bloque = int(request.GET.get("bloque", 1))
    except ValueError:
        bloque = 1
    if bloque not in dict(BLOQUES):
        bloque = 1
    categoria = request.GET.get("categoria", "")

    equipos = Equipo.objects.filter(activo=True)
    if categoria:
        equipos = equipos.filter(categoria=categoria)
    ocupados = set(Reserva.objects.filter(
        fecha=fecha, bloque=bloque, estado=Reserva.CONFIRMADA).values_list("equipo_id", flat=True))

    # Se agrupan las unidades por nombre: una tarjeta por tipo de equipo
    grupos = {}
    for e in equipos.order_by("nombre", "codigo"):
        g = grupos.setdefault(e.nombre, {"nombre": e.nombre, "categoria": e.categoria,
                                         "imagen": e.imagen, "total": 0, "libres": 0})
        g["total"] += 1
        g["libres"] += e.id not in ocupados

    return render(request, "catalogo.html", {
        "grupos": list(grupos.values()), "fecha": fecha, "bloque": bloque, "categoria": categoria,
        "bloques": BLOQUES, "categorias": [c[0] for c in Equipo.CATEGORIAS],
        "bloque_texto": dict(BLOQUES)[bloque],
    })


@login_required
@require_POST
def solicitar_lote(request):
    """Reserva N unidades de un mismo tipo de equipo para una fecha y bloque."""
    nombre = request.POST.get("nombre", "")
    volver = f"{reverse('catalogo')}?{urlencode({'fecha': request.POST.get('fecha', ''), 'bloque': request.POST.get('bloque', '')})}"
    fecha = parse_date(request.POST.get("fecha", ""))
    try:
        bloque = int(request.POST.get("bloque", ""))
        cantidad = int(request.POST.get("cantidad", ""))
    except ValueError:
        bloque = cantidad = 0
    if not fecha or bloque not in dict(BLOQUES) or cantidad < 1:
        messages.error(request, "Revisa la fecha, el bloque y la cantidad.")
        return redirect(volver)
    if fecha < timezone.localdate():
        messages.error(request, "La fecha no puede ser anterior a hoy.")
        return redirect(volver)

    ocupados = Reserva.objects.filter(fecha=fecha, bloque=bloque, estado=Reserva.CONFIRMADA).values_list("equipo_id", flat=True)
    libres = list(Equipo.objects.filter(activo=True, nombre=nombre).exclude(id__in=ocupados).order_by("codigo"))
    if cantidad > len(libres):
        messages.error(request, f"Solo hay {len(libres)} unidad(es) de «{nombre}» disponibles en ese bloque.")
        return redirect(volver)

    with transaction.atomic():
        creadas = [Reserva.objects.create(usuario=request.user, equipo=e, fecha=fecha, bloque=bloque)
                   for e in libres[:cantidad]]
    if len(creadas) == 1:
        return redirect("reserva_detalle", pk=creadas[0].pk)
    ids = ",".join(str(r.pk) for r in creadas)
    return redirect(f"{reverse('reserva_lote')}?ids={ids}")


@login_required
def reserva_lote(request):
    try:
        ids = [int(i) for i in request.GET.get("ids", "").split(",") if i]
    except ValueError:
        ids = []
    qs = Reserva.objects.select_related("equipo").filter(pk__in=ids).order_by("equipo__codigo")
    if not request.user.is_superuser:
        qs = qs.filter(usuario=request.user)
    reservas_lote = list(qs)
    if not reservas_lote:
        return redirect("reservas")
    return render(request, "reserva_lote.html", {"reservas": reservas_lote, "primera": reservas_lote[0]})


@login_required
def reservar(request, equipo_id):
    if request.user.is_superuser:
        return redirect("reserva_crear")
    equipo = get_object_or_404(Equipo, pk=equipo_id, activo=True)
    inicial = {"fecha": parse_date(request.GET.get("fecha", "")) or timezone.localdate(),
               "bloque": request.GET.get("bloque") or 1}
    form = ReservaForm(request.POST or None, initial=inicial, equipo=equipo, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        reserva = form.save()
        return redirect("reserva_detalle", pk=reserva.pk)
    return render(request, "reservar.html", {"form": form, "equipo": equipo})


@login_required
def reserva_detalle(request, pk):
    reserva = get_object_or_404(Reserva.objects.select_related("equipo", "usuario"), pk=pk)
    if reserva.usuario != request.user and not request.user.is_superuser:
        raise PermissionDenied
    return render(request, "reserva_detalle.html", {
        "reserva": reserva,
        "qr": qr_svg(f"{reserva.codigo}|{reserva.equipo.codigo}|{reserva.fecha}|B{reserva.bloque}"),
    })


@login_required
def reservas(request):
    qs = Reserva.objects.select_related("equipo", "usuario")
    if not request.user.is_superuser:
        qs = qs.filter(usuario=request.user)
    estado = request.GET.get("estado", "")
    q = request.GET.get("q", "").strip()
    if estado in (Reserva.CONFIRMADA, Reserva.CANCELADA):
        qs = qs.filter(estado=estado)
    if q and request.user.is_superuser:
        numero = q.upper().replace("#RES-", "")
        filtro = Q(usuario__username__icontains=q) | Q(equipo__nombre__icontains=q)
        if numero.isdigit():
            filtro |= Q(pk=int(numero))
        qs = qs.filter(filtro)
    return render(request, "reservas.html", {"reservas": qs, "estado": estado, "q": q})


@login_required
@require_POST
def reserva_cancelar(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if reserva.usuario != request.user and not request.user.is_superuser:
        raise PermissionDenied
    if reserva.estado == Reserva.CONFIRMADA:
        reserva.estado = Reserva.CANCELADA
        reserva.save(update_fields=["estado"])
        messages.success(request, f"La reserva {reserva.codigo} fue cancelada.")
    return redirect("reservas")


# ---------- Gestión del superusuario ----------

@solo_admin
def reserva_crear(request):
    form = ReservaAdminForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reserva = form.save()
        messages.success(request, f"Reserva {reserva.codigo} creada.")
        return redirect("reservas")
    return render(request, "reserva_form.html", {"form": form, "titulo": "Nueva solicitud"})


@solo_admin
def reserva_editar(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    form = ReservaAdminForm(request.POST or None, instance=reserva)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Reserva {reserva.codigo} actualizada.")
        return redirect("reservas")
    return render(request, "reserva_form.html", {"form": form, "titulo": f"Editar reserva {reserva.codigo}"})


@solo_admin
def reserva_eliminar(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if request.method == "POST":
        reserva.delete()
        messages.success(request, "La reserva fue eliminada.")
        return redirect("reservas")
    return render(request, "reserva_eliminar.html", {"reserva": reserva})


@solo_admin
def equipos(request):
    return render(request, "equipos.html", {"equipos": Equipo.objects.annotate(
        n_reservas=Count("reservas", filter=Q(reservas__estado=Reserva.CONFIRMADA)))})


@solo_admin
def usuarios(request):
    return render(request, "usuarios.html", {"usuarios": User.objects.select_related("perfil").annotate(
        n_reservas=Count("reservas")).order_by("username")})
