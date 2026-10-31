export const INITIAL_USER_STORIES = [
  {
    id: "HU-101",
    number: "HU-101",
    title: "Modificación de cobertura asociada a póliza activa",
    type: "Cambio",
    status: "revisada", // Borrador, En análisis, Pendiente de información, Generada, Revisada
    createdAt: "2026-09-22",
    updatedAt: "2026-09-23",
    requirementName: "Ajuste de coberturas en pólizas vigentes",
    infoType: "Minuta",
    description: "El departamento de operaciones requiere permitir a los ejecutivos modificar las coberturas contratadas en pólizas activas de seguro de vehículo, calculando el recargo o devolución proporcional en la prima sin cancelar la póliza original.",
    analysis: {
      knownData: [
        "Existe una póliza de seguro activa en el sistema.",
        "La solicitud corresponde a una modificación de coberturas existentes.",
        "El cálculo debe considerar el tiempo restante de vigencia de la póliza.",
        "Se requiere autorización para cambios con aumento de suma asegurada mayor al 20%."
      ],
      missingData: [
        "No se especifica si la fecha de vigencia del cambio puede ser retroactiva.",
        "No se indica el flujo de notificación al asegurado tras confirmar el cambio."
      ],
      assumptions: [
        "Se asume que la modificación se realiza sobre una póliza sin siniestros en trámite.",
        "Se asume que el sistema de tarificación responderá en tiempo real."
      ],
      ambiguities: [
        "No está claramente definido si el cambio aplica sobre pólizas ya emitidas en el ciclo anterior.",
        "Falta precisar el número máximo de modificaciones permitidas por periodo anual."
      ]
    },
    questions: [
      {
        id: "q1",
        category: "Reglas de negocio",
        question: "¿Permite el sistema aplicar vigencias retroactivas para la modificación de cobertura?",
        answer: "No, las modificaciones solo aplican a partir del primer día hábil siguiente a la aprobación.",
        status: "respondida"
      },
      {
        id: "q2",
        category: "Validaciones",
        question: "¿Qué ocurre si la póliza tiene un siniestro abierto al momento del cambio?",
        answer: "El sistema debe bloquear la modificación hasta que el ajuste del siniestro sea liquidado.",
        status: "respondida"
      },
      {
        id: "q3",
        category: "Notificaciones",
        question: "¿Debe enviarse un endoso digital firmado por correo electrónico al cliente?",
        answer: "",
        status: "pendiente"
      }
    ],
    userStory: {
      asA: "Ejecutivo de Operaciones de Seguros",
      iWant: "Modificar la cobertura asociada a una póliza activa de vehículo",
      soThat: "Pueda actualizar las condiciones contractuales del cliente sin emitir una nueva póliza desde cero."
    },
    acceptanceCriteria: [
      {
        id: "ac1",
        text: "El sistema debe validar que la póliza se encuentre en estado Activa y sin bloqueos judiciales.",
        given: "Dado que el ejecutivo ingresa el número de póliza activa",
        when: "Cuando selecciona la opción de modificar coberturas",
        then: "Entonces el sistema muestra el listado de coberturas disponibles para adicionar o eliminar."
      },
      {
        id: "ac2",
        text: "El sistema debe recalcular automáticamente el valor diferencial de la prima según los días restantes del periodo.",
        given: "Dado que el ejecutivo modifica el deducible o la suma asegurada",
        when: "Cuando presiona el botón recalcular prima",
        then: "Entonces el sistema muestra el desglose del ajuste financiero prorrateado."
      },
      {
        id: "ac3",
        text: "El cambio debe conservar el historial de modificaciones con usuario, fecha y marcas de auditoría.",
        given: "Dado que el cambio es confirmado y guardado",
        when: "Cuando se consulta la bitácora de la póliza",
        then: "Entonces se visualiza la versión previa y la nueva versión con el motivo del cambio."
      }
    ],
    pendingQuestions: [
      "¿Debe notificarse automáticamente al asegurado vía WhatsApp además de email?",
      "¿Requiere firma electrónica avanzada del cliente o basta con aceptación en portal?"
    ],
    observations: "Requiere coordinación previa con el equipo de Tarificación Core antes del pase a producción."
  },
  {
    id: "HU-102",
    number: "HU-102",
    title: "Emisión de Certificados de Cobertura en PDF",
    type: "Nueva Funcionalidad",
    status: "generada",
    createdAt: "2026-09-23",
    updatedAt: "2026-09-23",
    requirementName: "Descarga automatizada de certificados para clientes corporativos",
    infoType: "Descripción libre",
    description: "Los clientes empresariales necesitan descargar en cualquier momento sus certificados de cobertura vigentes en formato PDF oficial con código QR de verificación de autenticidad.",
    analysis: {
      knownData: [
        "El cliente se autentica en la banca en línea o portal corporativo.",
        "Los certificados deben incluir la firma digital de la aseguradora."
      ],
      missingData: [
        "Idioma alternativo requeridos para clientes multinacionales."
      ],
      assumptions: [
        "El código QR dirigirá a una URL de validación pública tokenizada."
      ],
      ambiguities: [
        "Tiempo de validez del código QR descargado."
      ]
    },
    questions: [
      {
        id: "q101",
        category: "Reglas de negocio",
        question: "¿El certificado debe generarse en tiempo real o en proceso por lotes (batch)?",
        answer: "Debe ser síncrono en tiempo real (menos de 3 segundos).",
        status: "respondida"
      }
    ],
    userStory: {
      asA: "Cliente Corporativo",
      iWant: "Generar y descargar el certificado de cobertura vigente en formato PDF",
      soThat: "Pueda presentarlo ante entidades regulatorias y licitaciones sin acudir a una sucursal."
    },
    acceptanceCriteria: [
      {
        id: "ac201",
        text: "El certificado PDF generado debe incluir logo institucional, resumen de coberturas, vigencia y código QR.",
        given: "Dado que el cliente selecciona una póliza activa",
        when: "Cuando hace clic en 'Descargar Certificado'",
        then: "Entonces se descarga un documento PDF con firma digital válida."
      }
    ],
    pendingQuestions: [
      "¿Permitir personalización de membrete corporativo en el PDF?"
    ],
    observations: "Revisar plantilla institucional con el departamento de mercadeo."
  },
  {
    id: "HU-103",
    number: "HU-103",
    title: "Notificación de Vencimiento de Póliza vía SMS",
    type: "Mejora",
    status: "en_analisis",
    createdAt: "2026-09-24",
    updatedAt: "2026-09-24",
    requirementName: "Envío de recordatorio previo al vencimiento",
    infoType: "Notas de conversación",
    description: "Enviar mensajes de texto automatizados 30, 15 y 5 días antes de la expiración de la póliza solicitando confirmación de renovación.",
    analysis: {
      knownData: [
        "Se usará el proveedor SMS transaccional actual."
      ],
      missingData: [
        "Límite de horario de envío para no molestar en horas nocturnas."
      ],
      assumptions: [
        "Los números de teléfono de los clientes están normalizados en formato E.164."
      ],
      ambiguities: [
        "Comportamiento si el cliente responde directamente al mensaje SMS."
      ]
    },
    questions: [
      {
        id: "q301",
        category: "Comportamiento esperado",
        question: "¿Qué ventana horaria está permitida para el envío masivo de mensajes?",
        answer: "",
        status: "pendiente"
      }
    ],
    userStory: {
      asA: "Gestor de Fidelización",
      iWant: "Programar avisos preventivos de expiración de póliza por SMS",
      soThat: "Aumente la tasa de renovación oportuna y disminuya la cartera vencida."
    },
    acceptanceCriteria: [
      {
        id: "ac301",
        text: "El sistema cron debe identificar pólizas a 30 días del vencimiento y encolar el SMS.",
        given: "Dado que una póliza está próxima a expirar",
        when: "Cuando se ejecuta la tarea diaria a las 09:00 AM",
        then: "Entonces se genera la orden de envío al proveedor de telefonía."
      }
    ],
    pendingQuestions: [
      "¿Incluir enlace corto con token de renovación directa con tarjeta de crédito?"
    ],
    observations: "Pendiente definir proveedor de acortador de URLs corporativo."
  },
  {
    id: "HU-104",
    number: "HU-104",
    title: "Consulta de Historial de Pagos y Facturación",
    type: "Integración",
    status: "borrador",
    createdAt: "2026-09-24",
    updatedAt: "2026-09-24",
    requirementName: "Visualización de recibos de prima en la App Móvil",
    infoType: "Otro",
    description: "Permitir a los asegurados consultar las cuotas pagadas y pendientes, descargando facturas electrónicas en formato XML y PDF.",
    analysis: {
      knownData: [
        "Conexión disponible con el API del sistema contable ERP."
      ],
      missingData: [
        "Definición de campos de retención de impuestos en facturación electrónica."
      ],
      assumptions: [
        "El cliente tiene acceso a internet continuo durante la consulta."
      ],
      ambiguities: [
        "Manejo de pagos en estado 'en procesamiento bancario'."
      ]
    },
    questions: [],
    userStory: {
      asA: "Asegurado Individual",
      iWant: "Consultar mi estado de cuenta y comprobantes tributarios",
      soThat: "Lleve un control claro de mis primas pagadas y deduzca impuestos."
    },
    acceptanceCriteria: [],
    pendingQuestions: [],
    observations: "En fase inicial de toma de requerimientos."
  }
];
