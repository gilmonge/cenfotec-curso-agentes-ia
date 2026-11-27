// Registro único de pantallas: de aquí salen las rutas de la aplicación y las opciones del menú.
// Agregar una pantalla = agregar una entrada. Si debe verse en el menú, se le pone «menu».
// Si solo deben verla quienes tengan una acción, se le pone «accion» (src/config/acciones.js).
// Ver docs/arquitectura.md y la skill «agregar-ruta».
import { LayoutDashboard, FileText, PlusCircle, HelpCircle, ShieldCheck, Bell } from 'lucide-react';
import { ACCION } from './acciones';
import { TableroComponent } from '../components/Dashboard/TableroComponent';
import { ListaHistoriaUsuarioComponent } from '../components/HistoriaUsuario/ListaHistoriaUsuarioComponent';
import { CrearHistoriaUsuarioComponent } from '../components/HistoriaUsuario/CrearHistoriaUsuarioComponent';
import { DetalleHistoriaUsuarioComponent } from '../components/HistoriaUsuario/DetalleHistoriaUsuarioComponent';
import { SolicitarCambioHistoriaComponent } from '../components/HistoriaUsuario/SolicitarCambioHistoriaComponent';
import { EditarHistoriaUsuarioComponent } from '../components/HistoriaUsuario/EditarHistoriaUsuarioComponent';
import { ListaHabilidadComponent } from '../components/Habilidad/ListaHabilidadComponent';
import { AyudaComponent } from '../components/Ayuda/AyudaComponent';
import { ListaLeccionComponent } from '../components/Leccion/ListaLeccionComponent';
import { MantenimientoComponent } from '../components/Mantenimiento/MantenimientoComponent';
import { PendientesComponent } from '../components/Pendientes/PendientesComponent';

// ruta: relativa a la raíz ('' es el inicio). componente: lo que se muestra.
// accion (opcional): acción (o lista; basta una) que hace falta para abrirla. menu.accion la reemplaza solo
// para mostrar la opción en el menú.
// menu (opcional): etiqueta, corta (en la barra inferior del móvil, máximo 9 letras), título (texto
// emergente), ícono, orden, si la ruta debe coincidir exacta y contador (el número que se muestra al lado).
export const listaRuta = Object.freeze([
  {
    ruta: '',
    componente: TableroComponent,
    menu: { etiqueta: 'Inicio', corta: 'Inicio', titulo: 'Ir al inicio', icono: LayoutDashboard, orden: 10, exacta: true },
  },
  {
    ruta: 'pendientes',
    componente: PendientesComponent,
    menu: { etiqueta: 'Pendientes', corta: 'Avisos', titulo: 'Lo que espera su decisión y sus avisos', icono: Bell, orden: 15, contador: 'pendientes' },
  },
  {
    ruta: 'historias',
    componente: ListaHistoriaUsuarioComponent,
    accion: ACCION.HISTORIA_VER,
    menu: { etiqueta: 'Historias de usuario', corta: 'Historias', titulo: 'Ver las historias de usuario', icono: FileText, orden: 20, exacta: true },
  },
  {
    ruta: 'historias/nueva',
    componente: CrearHistoriaUsuarioComponent,
    // También se abre para retomar una historia en proceso: responder a negocio o decidir como Product Owner.
    accion: [ACCION.HISTORIA_CREAR, ACCION.HISTORIA_RESPONDER_NEGOCIO, ACCION.HISTORIA_APROBAR,
      ACCION.HISTORIA_DEVOLVER, ACCION.HISTORIA_RECHAZAR],
    menu: { etiqueta: 'Nueva historia', corta: 'Nueva', titulo: 'Crear una historia nueva', icono: PlusCircle, orden: 30, accion: ACCION.HISTORIA_CREAR },
  },
  { ruta: 'historias/:id', componente: DetalleHistoriaUsuarioComponent, accion: ACCION.HISTORIA_VER },
  { ruta: 'historias/:id/editar', componente: EditarHistoriaUsuarioComponent, accion: ACCION.HISTORIA_EDITAR },
  { ruta: 'historias/:id/solicitar-cambio', componente: SolicitarCambioHistoriaComponent, accion: ACCION.CAMBIO_SOLICITAR },
  { ruta: 'lecciones', componente: ListaLeccionComponent, accion: ACCION.LECCION_VER },
  { ruta: 'skills', componente: ListaHabilidadComponent },
  {
    ruta: 'mantenimiento',
    componente: MantenimientoComponent,
    accion: ACCION.MANTENIMIENTO_VER,
    menu: { etiqueta: 'Mantenimiento', corta: 'Usuarios', titulo: 'Usuarios, roles y acciones', icono: ShieldCheck, orden: 80 },
  },
  {
    ruta: 'ayuda',
    componente: AyudaComponent,
    menu: { etiqueta: 'Ayuda', corta: 'Ayuda', titulo: 'Ver Ayuda', icono: HelpCircle, orden: 90 },
  },
]);

// Opciones del menú principal, en su orden. «puede» filtra las que la persona no tiene permitidas.
export const listaOpcionMenu = (puede = () => true) => listaRuta
  .filter((entrada) => entrada.menu && puede(entrada.menu.accion ?? entrada.accion))
  .map(({ ruta, menu: { accion: _accion, ...menu } }) => ({ ...menu, destino: `/${ruta}` }))
  .sort((a, b) => a.orden - b.orden);
