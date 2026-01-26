# Inventario + Forecast (Django + FastAPI)

## Estructura
- `backend_django/`: API REST con Django + DRF para productos y ventas.
- `ml_fastapi/`: microservicio FastAPI que calcula forecasts básicos.
- `requirements.txt`: dependencias mínimas para ambos servicios.

## Puesta en marcha rápida
1) Crear venv e instalar deps:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```
2) Migraciones y superusuario:
```bash
cd backend_django
python manage.py migrate
python manage.py createsuperuser
```
3) Levantar servicios:
```bash
# Terminal 1
cd backend_django
python manage.py runserver 8000

# Terminal 2
cd ml_fastapi
uvicorn main:app --reload --port 8001
```

## Endpoints clave (Django)
- CRUD productos: `GET/POST http://127.0.0.1:8000/api/products/`
- CRUD ventas: `GET/POST http://127.0.0.1:8000/api/sales/`
- Forecast por producto: `GET http://127.0.0.1:8000/api/products/<id>/forecast/?horizon=12&freq=M`

## Notas
- `FASTAPI_URL` configurable vía env var en `backend_django/config/settings.py` (default `http://127.0.0.1:8001`).
- El histórico se agrega mensualmente y rellena meses sin ventas con 0 para un input limpio al modelo.
