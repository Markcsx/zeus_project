# Inventario + Forecast (Django)

## Estructura
- `backend_django/`: API REST y panel admin.
- `requirements.txt`: dependencias mínimas.

## Puesta en marcha (Windows)
1) Crear venv e instalar dependencias:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
2) Migrar BD y crear superusuario:
```bash
cd backend_django
python manage.py migrate
python manage.py createsuperuser
```
3) Levantar servidor:
```bash
cd backend_django
python manage.py runserver 8000
```

## Uso del panel admin
- URL: `http://127.0.0.1:8000/` (redirige al admin).
- Productos:
  - El SKU se genera solo si lo dejas vacío.
  - La acción “Ver forecast API” (en el menú de acciones) abre directamente el endpoint de forecast del producto seleccionado.
  - Asegúrate de definir `price`: se usa para convertir monto vendido en unidades (total_price / price).
- Ventas:
  - Botón “Importar CSV” en la lista de ventas.
  - El CSV acepta separador `;` o `,` y decimales con coma o punto.
  - Encabezados esperados: `sku,date,serial_number,client_name,total_price`.
  - Si falta `sku` y existe **un solo** producto, se asigna ese producto por defecto.
  - `serial_number` se autogenera si viene vacío.

## API REST
- Productos: `GET/POST http://127.0.0.1:8000/api/products/`
- Ventas: `GET/POST http://127.0.0.1:8000/api/sales/`
  - Filtros: `?id=`, `?client_name=`, `?date=YYYY-MM-DD`.
- Forecast simple por producto: `GET http://127.0.0.1:8000/api/products/<id>/forecast/`
  - Lógica: agrega ventas por mes, convierte monto a unidades con `total_price / price` y usa el último mes como predicción del siguiente.
  - Respuesta incluye `forecast_month`, `predicted_sales_units`, `stock_shortage`, `stock_required` y el `history` mensual.

## Flujo recomendado (sin errores)
1) Crear al menos un Producto en el admin y definir su `price` y `stock`.
2) Importar las ventas vía CSV desde el admin (usar UTF-8).
3) Revisar las ventas en `/api/sales/` si necesitas filtros.
4) Obtener forecast del producto desde el admin (acción “Ver forecast API”) o vía `GET /api/products/<id>/forecast/`.
5) Ajustar stock según `stock_shortage` reportado.
