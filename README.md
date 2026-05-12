# Zeus Inventory

Sistema de inventario y forecast para autopartes. Incluye:

- Dashboard web en Django: productos, ventas, graficas, filtros y forecast.
- API REST con Django REST Framework.
- Catalogo base de 40 productos automotrices realistas para Peru.
- Forecast por producto usando TensorFlow cuando hay historial suficiente.
- Servicio FastAPI opcional para exponer forecast como microservicio.

## Requisitos

- Python 3.12 o 3.13.
- Git.
- Windows PowerShell, CMD, Git Bash o terminal equivalente.

> Nota: TensorFlow es una dependencia pesada. Si la instalacion falla, actualiza `pip` primero y verifica que estes usando una version compatible de Python.

## Instalacion desde cero

Clona el repositorio:

```bash
git clone <URL_DEL_REPOSITORIO>
cd zeus_project
```

Crea y activa un entorno virtual.

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

En Windows CMD:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

En macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Actualiza `pip` e instala dependencias:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Preparar la base de datos

Entra al proyecto Django:

```bash
cd backend_django
```

Ejecuta migraciones:

```bash
python manage.py migrate
```

Carga el catalogo base de 40 productos:

```bash
python manage.py seed_catalog
```

Crea un usuario administrador:

```bash
python manage.py createsuperuser
```

Sigue las preguntas de la terminal para definir usuario, email y password.

## Ejecutar el servidor Django

Desde `backend_django`:

```bash
python manage.py runserver 8000
```

Abre estas URLs:

- Dashboard: `http://127.0.0.1:8000/app/`
- Admin Django: `http://127.0.0.1:8000/admin/`
- API productos: `http://127.0.0.1:8000/api/products/`
- API ventas: `http://127.0.0.1:8000/api/sales/`

Para detener el servidor, usa `Ctrl + C` en la terminal.

## Flujo recomendado para probar

1. Abre `http://127.0.0.1:8000/app/`.
2. Revisa la tabla de productos. Deben existir 40 productos.
3. Crea ventas desde el formulario del dashboard o desde el admin.
4. Usa filtros por producto, cliente, fecha o categoria.
5. En la seccion Forecast, selecciona un producto y pulsa `Consultar forecast`.

## Importar ventas por CSV

Desde el admin de Django:

1. Entra a `http://127.0.0.1:8000/admin/`.
2. Abre `Sales`.
3. Usa el boton `Importar CSV`.

El CSV acepta separador `;` o `,`.

Columnas esperadas:

```csv
sku,date,serial_number,client_name,total_price
```

Ejemplo:

```csv
FIL-ACE-001,2026-05-01,SER-0001,Cliente Demo,42.90
PAS-FRE-005,2026-05-02,SER-0002,Taller Lima Norte,148.00
```

## Ejecutar tests y checks

Desde `backend_django`:

```bash
python manage.py check
python manage.py test inventory
```

## Servicio FastAPI opcional

El proyecto incluye un microservicio opcional en `ml_fastapi/`.

Desde la raiz del repositorio, con el entorno virtual activo:

```bash
uvicorn ml_fastapi.main:app --reload --port 8001
```

URL de documentacion FastAPI:

```text
http://127.0.0.1:8001/docs
```

## Estructura principal

```text
zeus_project/
├── backend_django/
│   ├── config/
│   ├── inventory/
│   │   ├── static/inventory/
│   │   ├── templates/inventory/
│   │   ├── management/commands/seed_catalog.py
│   │   ├── api_views.py
│   │   ├── forecasting.py
│   │   ├── models.py
│   │   └── serializers.py
│   └── manage.py
├── ml_fastapi/
│   └── main.py
├── requirements.txt
└── README.md
```

## Comandos rapidos

Primera vez:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cd backend_django
python manage.py migrate
python manage.py seed_catalog
python manage.py createsuperuser
python manage.py runserver 8000
```

Siguientes veces:

```bash
.\.venv\Scripts\Activate.ps1
cd backend_django
python manage.py runserver 8000
```
