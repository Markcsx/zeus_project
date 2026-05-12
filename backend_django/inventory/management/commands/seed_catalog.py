from decimal import Decimal

from django.core.management.base import BaseCommand

from inventory.models import Product


CATALOG = [
    ("FIL-ACE-001", "Filtro de aceite Toyota Hilux 2.8", "Filtros", "42.90", 320, 60, "Filtro compatible con camionetas pickup de alta rotacion."),
    ("FIL-AIR-002", "Filtro de aire Toyota Corolla/Yaris", "Filtros", "38.50", 360, 70, "Filtro de aire para mantenimiento preventivo urbano."),
    ("FIL-CAB-003", "Filtro de cabina carbon activo", "Filtros", "55.00", 240, 45, "Filtro antipolen para sedanes y SUV compactas."),
    ("FIL-COM-004", "Filtro de combustible diesel common rail", "Filtros", "86.00", 180, 35, "Filtro para motores diesel de uso comercial."),
    ("PAS-FRE-005", "Pastillas de freno delanteras ceramicas", "Frenos", "148.00", 260, 50, "Juego delantero para autos y SUV medianas."),
    ("PAS-POS-006", "Pastillas de freno posteriores semimetalicas", "Frenos", "126.00", 220, 42, "Juego posterior para servicio de mantenimiento."),
    ("DIS-FRE-007", "Disco de freno ventilado delantero", "Frenos", "189.00", 170, 30, "Disco ventilado para frenado intensivo en ciudad."),
    ("ZAP-FRE-008", "Zapatas de freno posterior pickup", "Frenos", "132.00", 145, 28, "Juego de zapatas para camionetas de trabajo."),
    ("LIQ-FRE-009", "Liquido de frenos DOT 4 500ml", "Frenos", "24.90", 420, 90, "Fluido DOT 4 para servicio rapido."),
    ("BAT-60A-010", "Bateria 60Ah libre mantenimiento", "Baterias", "389.00", 130, 24, "Bateria sellada para autos compactos y sedanes."),
    ("BAT-75A-011", "Bateria 75Ah libre mantenimiento", "Baterias", "489.00", 110, 20, "Bateria para SUV y camionetas ligeras."),
    ("ALT-12V-012", "Alternador 12V 90A reconstruido", "Electrico", "520.00", 54, 10, "Alternador con garantia para flotas urbanas."),
    ("ARR-12V-013", "Arrancador 12V 1.4kW", "Electrico", "460.00", 48, 9, "Motor de arranque para reemplazo preventivo."),
    ("BUJ-IRI-014", "Bujia iridium alto rendimiento", "Encendido", "52.00", 520, 120, "Bujia de larga duracion para motores gasolina."),
    ("BOB-ENC-015", "Bobina de encendido individual", "Encendido", "168.00", 160, 32, "Bobina tipo lapiz para motores modernos."),
    ("CAB-BUJ-016", "Cable de bujias siliconado", "Encendido", "96.00", 140, 28, "Set de cables para mantenimiento de encendido."),
    ("COR-DIS-017", "Correa de distribucion reforzada", "Motor", "118.75", 210, 42, "Correa reforzada para servicio de motor."),
    ("COR-ALT-018", "Correa alternador multicanal", "Motor", "68.00", 250, 50, "Correa auxiliar para alternador y accesorios."),
    ("BOM-AGU-019", "Bomba de agua automotriz", "Refrigeracion", "176.40", 150, 30, "Bomba de agua para sistema de refrigeracion."),
    ("RAD-ALU-020", "Radiador aluminio compacto", "Refrigeracion", "420.00", 70, 12, "Radiador para sedan y SUV compacta."),
    ("TER-MOT-021", "Termostato de motor 82 grados", "Refrigeracion", "64.00", 190, 38, "Termostato para control de temperatura."),
    ("REF-ROJ-022", "Refrigerante rojo larga vida 1 galon", "Refrigeracion", "39.90", 360, 80, "Refrigerante de larga vida para taller."),
    ("AMO-DEL-023", "Amortiguador delantero gas", "Suspension", "235.50", 140, 28, "Amortiguador delantero para uso mixto ciudad/carretera."),
    ("AMO-POS-024", "Amortiguador posterior gas", "Suspension", "218.00", 130, 26, "Amortiguador posterior para mantenimiento general."),
    ("ROT-SUS-025", "Rotula de suspension inferior", "Suspension", "92.00", 180, 35, "Rotula inferior para tren delantero."),
    ("TER-DIR-026", "Terminal de direccion exterior", "Direccion", "78.00", 170, 34, "Terminal para sistema de direccion mecanica/hidraulica."),
    ("ACE-5W3-027", "Aceite sintetico 5W-30 4L", "Lubricantes", "159.90", 300, 70, "Aceite sintetico para mantenimiento premium."),
    ("ACE-10W-028", "Aceite semisintetico 10W-40 4L", "Lubricantes", "118.90", 340, 75, "Aceite semisintetico de alta rotacion."),
    ("GRS-LIT-029", "Grasa multiproposito litio 400g", "Lubricantes", "32.00", 260, 55, "Grasa para servicio de rodamientos y articulaciones."),
    ("FAR-LED-030", "Faro LED delantero derecho", "Iluminacion", "315.00", 82, 15, "Faro LED de reemplazo para SUV compacta."),
    ("FOC-H4X-031", "Foco halogeno H4 12V", "Iluminacion", "28.00", 450, 95, "Foco halogeno estandar para reposicion rapida."),
    ("PLU-LIM-032", "Plumilla limpiaparabrisas 22 pulgadas", "Accesorios", "34.90", 380, 85, "Plumilla universal para temporada de lluvias."),
    ("SEN-OXI-033", "Sensor de oxigeno universal", "Sensores", "165.90", 150, 30, "Sensor lambda universal para diagnostico de emisiones."),
    ("SEN-ABS-034", "Sensor ABS delantero", "Sensores", "142.00", 95, 18, "Sensor ABS para tren delantero."),
    ("KIT-EMB-035", "Kit de embrague 3 piezas", "Transmision", "690.00", 46, 8, "Kit completo de embrague para taxi y uso urbano."),
    ("RET-CIG-036", "Reten de ciguenal posterior", "Motor", "58.00", 160, 32, "Reten posterior para reparacion de motor."),
    ("ESC-FLE-037", "Flexible de escape mallado", "Escape", "88.00", 120, 24, "Flexible de escape para reparacion rapida."),
    ("NEU-185-038", "Neumatico 185/65R15 turismo", "Neumaticos", "285.00", 95, 20, "Neumatico urbano de alta rotacion."),
    ("NEU-265-039", "Neumatico 265/65R17 pickup", "Neumaticos", "620.00", 64, 12, "Neumatico para pickup y carretera."),
    ("GAT-HID-040", "Gata hidraulica botella 4 toneladas", "Herramientas", "135.00", 72, 14, "Herramienta de apoyo para taller y auxilio."),
]


class Command(BaseCommand):
    help = "Carga o actualiza el catalogo base de 40 productos automotrices."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for sku, name, category, price, stock, stock_min, description in CATALOG:
            _, was_created = Product.objects.update_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": category,
                    "description": description,
                    "price": Decimal(price),
                    "stock_initial": stock,
                    "stock": stock,
                    "stock_min": stock_min,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Catalogo listo: {created} creados, {updated} actualizados."))
