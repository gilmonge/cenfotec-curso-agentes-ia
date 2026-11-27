# Mapa de módulos: pólizas demo

Versión del fixture: **1.1.0**.

Este repositorio es completamente ficticio. Usa claves `DEMO-`, montos didácticos y
operaciones en memoria. No contiene datos personales ni integra aseguradoras,
bancos, servicios externos, bases de datos o sistemas reales. La fórmula de prima
es ilustrativa y no es asesoría ni tarifa actuarial.

## Módulos

| Módulo | Responsabilidad | Dependencias directas |
|---|---|---|
| `modelos.py` | Tipos de póliza, cobertura, pago y propuesta de renovación | Biblioteca estándar |
| `servicios/validaciones.py` | Prefijo demo, producto, fechas y prima no negativa | `modelos.py` |
| `servicios/polizas.py` | Crear y activar una póliza en memoria | `modelos.py`, `validaciones.py` |
| `servicios/coberturas.py` | Catálogo demo y asociación de coberturas | `modelos.py` |
| `servicios/primas.py` | Cálculo ilustrativo y redondeo de prima | `modelos.py` |
| `servicios/renovaciones.py` | Propuesta de nueva fecha e importe, sin mutar la póliza | `modelos.py`, `validaciones.py`, `primas.py` |
| `servicios/pagos.py` | Recibo de pago simulado, sin mover fondos | `modelos.py` |
| `clientes/modelo_cliente.py` | Datos del cliente y formato de fecha | Biblioteca estándar |
| `clientes/pantalla_cliente.py` | Pantalla «Datos del cliente» y sus validaciones | `modelo_cliente.py` |
| `notificaciones/aviso_cliente.py` | Avisos de bienvenida por correo y mensaje de texto | `modelo_cliente.py` |
| `reportes/exportacion_cliente.py` | Exportación «Clientes activos» | `modelo_cliente.py` |
| `cargas/carga_cliente.py` | Carga masiva de clientes por archivo | `modelo_cliente.py` |

## Dependencias y procesos críticos

```text
modelos
  ├── validaciones ── polizas
  ├── coberturas
  ├── primas
  ├── validaciones ── renovaciones
  └── pagos

clientes.modelo_cliente
  ├── pantalla_cliente
  ├── aviso_cliente
  ├── exportacion_cliente
  └── carga_cliente

Alta: validar datos → crear borrador → asociar coberturas → calcular prima → activar.
Renovación: validar vigencia → proponer fecha e importe → decisión externa fuera de este demo.
Pago: validar importe → emitir recibo simulado; no existe liquidación ni reembolso.
```

Este mapa describe módulos, no campos: para saber dónde se usa un campo hay que buscarlo
en el código. Los cambios de reglas de validación afectan alta y renovación. Los cambios al modelo
`Poliza` pueden afectar cobertura, prima, pago y renovación. Un cambio al cálculo de
prima puede afectar alta y propuesta de renovación. No hay evidencia aquí sobre
arquitectura, integración, almacenamiento o procesos de ninguna aplicación real.
