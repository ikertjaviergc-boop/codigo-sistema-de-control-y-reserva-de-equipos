from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Perfil, Reserva


class RegistroForm(UserCreationForm):
    tipo = forms.ChoiceField(choices=Perfil.TIPOS, label="Tipo de usuario")
    departamento = forms.CharField(max_length=80, required=False, label="Departamento")

    class Meta:
        model = User
        fields = ("username", "first_name")
        labels = {"username": "RUT", "first_name": "Nombre completo"}
        help_texts = {"username": ""}

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Perfil.objects.create(user=user, tipo=self.cleaned_data["tipo"],
                                  departamento=self.cleaned_data["departamento"])
        return user


class ReservaForm(forms.ModelForm):
    """Formulario del usuario normal: el equipo y el usuario vienen fijos."""

    class Meta:
        model = Reserva
        fields = ("fecha", "bloque")
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, equipo=None, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.equipo = equipo
        self.instance.usuario = usuario

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha < timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser anterior a hoy.")
        return fecha


class ReservaAdminForm(forms.ModelForm):
    """Formulario del superusuario: controla todos los campos."""

    class Meta:
        model = Reserva
        fields = ("usuario", "equipo", "fecha", "bloque", "estado")
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
