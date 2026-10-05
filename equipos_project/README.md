# Sistema de control y reserva de equipos (Django)

## Puesta en marcha
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations reservas
python manage.py migrate
python manage.py createsuperuser                      # este será el encargado
python manage.py runserver
```
- Sitio: http://127.0.0.1:8000/
- Agrega los primeros equipos desde el botón «Agregar equipo» (Equipos) o en /admin/.

## Roles
- **Superusuario (encargado):** ve, crea, edita, elimina y cancela cualquier solicitud; ve Equipos y Usuarios.
- **Usuario normal (docente/estudiante):** solo solicita equipos y cancela sus propias reservas.

## Sesión
La sesión se guarda en una cookie (30 días). Si desmarcas «Mantener sesión iniciada», la cookie se borra al cerrar el navegador.

## Cargar equipos iniciales
```bash
python manage.py makemigrations reservas && python manage.py migrate
python manage.py cargar_equipos      # 5 cámaras (CAM-001..005), 10 proyectores (PROY-001..010), 25 laptops (LAP-001..025)
```
Se puede repetir sin duplicar. Las fotos están en `media/equipos/`.
