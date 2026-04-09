// AI Context Protocol Types and Utilities
// This module provides a semantic UI map so the agent can reason about
// what each screen contains without requiring computer vision.

export interface ScreenRegion {
  region_id: string
  label: string
  position: string
  description: string
}

export interface ScreenElement {
  element_id: string
  label: string
  selector: string | null
  kind: "nav" | "header" | "button" | "input" | "metric" | "list" | "table" | "card" | "modal" | "toggle" | "link" | "status"
  position: string
  interactive: boolean
  description: string
}

export interface DemoStep {
  step: number
  title: string
  description: string
  focus_selectors: string[]
}

export interface NavigationHint {
  section_id: string
  label: string
  selector: string
  description: string
}

export interface ScreenContext {
  current_view: string
  current_path: string
  screen_title: string
  screen_goal: string
  user_context: {
    store_id: string | null
    store_name: string | null
    is_authenticated: boolean
  }
  allowed_actions: string[]
  required_fields: Record<string, string[]>
  navigation_hints: NavigationHint[]
  data_available: string[]
  layout_notes: string
  layout_regions: ScreenRegion[]
  key_elements: ScreenElement[]
  demo_steps: DemoStep[]
  talking_points: string[]
  timestamp: string
}

export interface AITool {
  name: string
  description: string
  parameters: Record<string, {
    type: string
    required: boolean
    description: string
  }>
}

export interface AIContextPayload {
  screen: ScreenContext
  available_tools: AITool[]
  active_tool: string | null
  last_action: string | null
  navigation_function: string
}

function buildPath(screen: string) {
  switch (screen) {
    case "login":
      return "/auth/login"
    case "register":
      return "/auth/register"
    case "forgot-password":
      return "/auth/forgot-password"
    case "dashboard":
      return "/"
    default:
      return `/${screen}`
  }
}

// Screen context configurations for each section
export const screenContexts: Record<string, Omit<ScreenContext, "timestamp" | "user_context" | "current_path">> = {
  login: {
    current_view: "login",
    screen_title: "Inicio de sesión",
    screen_goal: "Permitir que el aliado acceda al portal con su correo y contraseña.",
    allowed_actions: ["enter_credentials", "submit_login", "open_register", "open_forgot_password"],
    required_fields: {
      submit_login: ["email", "password"],
    },
    navigation_hints: [
      { section_id: "forgot-password", label: "Olvidaste tu contraseña", selector: "[data-action='forgot-password']", description: "Enlace pequeño debajo del campo de contraseña" },
      { section_id: "register", label: "Regístrate aquí", selector: "[data-action='register']", description: "Enlace al final de la tarjeta de login" },
    ],
    data_available: ["test_credentials", "validation_errors", "auth_status"],
    layout_notes: "Pantalla pública con fondo degradado y una sola tarjeta centrada. Logo arriba, formulario en el centro y credenciales de prueba en la parte inferior.",
    layout_regions: [
      { region_id: "auth-card", label: "Tarjeta principal", position: "center", description: "Contenedor blanco centrado con el logo, título y formulario." },
      { region_id: "auth-form", label: "Formulario", position: "center-middle", description: "Campos de correo y contraseña, más enlaces secundarios y CTA principal." },
      { region_id: "auth-help", label: "Credenciales de prueba", position: "center-bottom", description: "Caja gris con el correo y contraseña demo." },
    ],
    key_elements: [
      { element_id: "login-email", label: "Correo electrónico", selector: "#email", kind: "input", position: "center-middle", interactive: true, description: "Primer campo del formulario." },
      { element_id: "login-password", label: "Contraseña", selector: "#password", kind: "input", position: "center-middle", interactive: true, description: "Segundo campo, debajo del correo." },
      { element_id: "login-submit", label: "Iniciar sesión", selector: "[data-action='login']", kind: "button", position: "center-middle", interactive: true, description: "CTA principal rojo que ocupa todo el ancho." },
      { element_id: "login-forgot", label: "Olvidaste tu contraseña", selector: "[data-action='forgot-password']", kind: "link", position: "center-middle-right", interactive: true, description: "Enlace pequeño alineado a la derecha arriba del CTA principal." },
      { element_id: "login-register", label: "Regístrate aquí", selector: "[data-action='register']", kind: "link", position: "center-bottom", interactive: true, description: "Enlace textual debajo del botón principal." },
      { element_id: "login-demo-credentials", label: "Credenciales demo", selector: null, kind: "card", position: "center-bottom", interactive: false, description: "Caja informativa con admin@latoscana.com y demo123." },
    ],
    demo_steps: [
      { step: 1, title: "Orientar la vista", description: "Explicar que la tarjeta central reúne todo el acceso.", focus_selectors: ["#email", "#password", "[data-action='login']"] },
      { step: 2, title: "Mostrar acceso demo", description: "Recordar las credenciales de prueba visibles al final de la tarjeta.", focus_selectors: [] },
    ],
    talking_points: [
      "Todo el flujo está concentrado en una tarjeta centrada para reducir fricción.",
      "El CTA principal es el botón rojo de inicio de sesión.",
      "Las rutas de recuperación y registro están visibles sin salir de la misma pantalla.",
    ],
  },
  register: {
    current_view: "register",
    screen_title: "Registro",
    screen_goal: "Crear una cuenta nueva para el negocio.",
    allowed_actions: ["complete_registration", "return_to_login"],
    required_fields: {
      complete_registration: ["name", "email", "storeName", "password", "confirmPassword"],
    },
    navigation_hints: [
      { section_id: "login", label: "Volver al inicio", selector: "#register-back-btn", description: "Botón en la parte superior de la tarjeta" },
    ],
    data_available: ["registration_fields", "validation_errors"],
    layout_notes: "Tarjeta centrada con botón de regreso arriba, título de registro y cinco campos apilados verticalmente.",
    layout_regions: [
      { region_id: "register-header", label: "Encabezado", position: "center-top", description: "Botón de regreso y título Crear Cuenta." },
      { region_id: "register-form", label: "Formulario de alta", position: "center-middle", description: "Campos de nombre, correo, negocio y contraseña." },
    ],
    key_elements: [
      { element_id: "register-back", label: "Volver al inicio", selector: "#register-back-btn", kind: "button", position: "center-top-left", interactive: true, description: "Botón textual con ícono de flecha." },
      { element_id: "register-name", label: "Nombre completo", selector: "#name", kind: "input", position: "center-middle", interactive: true, description: "Primer campo del formulario." },
      { element_id: "register-email", label: "Correo electrónico", selector: "#email", kind: "input", position: "center-middle", interactive: true, description: "Segundo campo." },
      { element_id: "register-store-name", label: "Nombre del negocio", selector: "#storeName", kind: "input", position: "center-middle", interactive: true, description: "Campo para el nombre comercial." },
      { element_id: "register-submit", label: "Crear Cuenta", selector: "#register-submit-btn", kind: "button", position: "center-bottom", interactive: true, description: "CTA principal a ancho completo." },
    ],
    demo_steps: [
      { step: 1, title: "Mostrar formulario de alta", description: "Explicar que el formulario pide datos personales y del negocio.", focus_selectors: ["#name", "#email", "#storeName"] },
      { step: 2, title: "Cerrar con CTA", description: "Señalar el botón final Crear Cuenta.", focus_selectors: ["#register-submit-btn"] },
    ],
    talking_points: [
      "El registro está pensado como un flujo lineal de una sola tarjeta.",
      "Hay un botón de retorno arriba para volver al login sin perder contexto.",
    ],
  },
  "forgot-password": {
    current_view: "forgot-password",
    screen_title: "Recuperar contraseña",
    screen_goal: "Enviar instrucciones de recuperación al correo del aliado.",
    allowed_actions: ["request_password_reset", "return_to_login"],
    required_fields: {
      request_password_reset: ["email"],
    },
    navigation_hints: [
      { section_id: "login", label: "Volver al inicio", selector: "#forgot-back-btn", description: "Botón de regreso en el encabezado de la tarjeta" },
    ],
    data_available: ["recovery_email", "success_state", "error_state"],
    layout_notes: "Tarjeta centrada con icono de correo, descripción breve, un solo campo de email y un botón principal.",
    layout_regions: [
      { region_id: "forgot-header", label: "Encabezado", position: "center-top", description: "Botón de regreso, ícono y texto explicativo." },
      { region_id: "forgot-form", label: "Formulario", position: "center-middle", description: "Campo de correo y CTA de envío." },
    ],
    key_elements: [
      { element_id: "forgot-back", label: "Volver al inicio", selector: "#forgot-back-btn", kind: "button", position: "center-top-left", interactive: true, description: "Botón textual para regresar." },
      { element_id: "forgot-email", label: "Correo electrónico", selector: "#email", kind: "input", position: "center-middle", interactive: true, description: "Único campo requerido en esta vista." },
      { element_id: "forgot-submit", label: "Enviar instrucciones", selector: "#forgot-submit-btn", kind: "button", position: "center-bottom", interactive: true, description: "CTA rojo a ancho completo." },
    ],
    demo_steps: [
      { step: 1, title: "Explicar simplicidad", description: "Mostrar que sólo se necesita el correo de la cuenta.", focus_selectors: ["#email"] },
      { step: 2, title: "Cerrar con CTA", description: "Señalar el botón Enviar instrucciones.", focus_selectors: ["#forgot-submit-btn"] },
    ],
    talking_points: [
      "Es una pantalla simple, pensada para recuperación rápida.",
      "Después del envío aparece un estado de éxito con el correo confirmado.",
    ],
  },
  dashboard: {
    current_view: "dashboard",
    screen_title: "Dashboard",
    screen_goal: "Mostrar el resumen diario del negocio y el estado operativo general.",
    allowed_actions: ["view_metrics", "navigate_to_section", "view_orders"],
    required_fields: {},
    navigation_hints: [
      { section_id: "catalog", label: "Catálogo", selector: "#nav-catalog", description: "Ítem de menú en sidebar izquierdo" },
      { section_id: "finances", label: "Finanzas", selector: "#nav-finances", description: "Ítem de menú en sidebar izquierdo" },
      { section_id: "disputes", label: "Disputas", selector: "#nav-disputes", description: "Ítem de menú en sidebar izquierdo" },
      { section_id: "schedule", label: "Horarios", selector: "#nav-schedule", description: "Ítem de menú en sidebar izquierdo" },
      { section_id: "support", label: "Soporte", selector: "#nav-support", description: "Ítem de menú en sidebar izquierdo" },
    ],
    data_available: ["sales_today", "orders_today", "active_orders", "average_rating", "recent_orders"],
    layout_notes: "Layout con sidebar fija a la izquierda y contenido principal a la derecha. Arriba hay un header con CTA, luego métricas en grilla y al final una lista de pedidos recientes.",
    layout_regions: [
      { region_id: "sidebar", label: "Barra lateral", position: "left", description: "Navegación persistente entre secciones." },
      { region_id: "dashboard-header", label: "Encabezado", position: "main-top", description: "Título, subtítulo y botón Simular Pedido al extremo derecho." },
      { region_id: "primary-metrics", label: "Métricas principales", position: "main-upper", description: "Cuatro tarjetas con ventas, pedidos, pedidos activos y rating." },
      { region_id: "secondary-metrics", label: "Métricas secundarias", position: "main-middle", description: "Tarjetas de crecimiento semanal y disputas pendientes." },
      { region_id: "recent-orders", label: "Pedidos recientes", position: "main-bottom", description: "Listado vertical de órdenes con estado y total." },
    ],
    key_elements: [
      { element_id: "sidebar-catalog", label: "Nav Catálogo", selector: "#nav-catalog", kind: "nav", position: "left", interactive: true, description: "Acceso a la gestión de productos." },
      { element_id: "sidebar-finances", label: "Nav Finanzas", selector: "#nav-finances", kind: "nav", position: "left", interactive: true, description: "Acceso a pagos y dispersiones." },
      { element_id: "dashboard-cta", label: "Simular Pedido", selector: "#dashboard-simulate-order-btn", kind: "button", position: "main-top-right", interactive: true, description: "Botón rojo del header usado para generar una notificación demo." },
      { element_id: "dashboard-metrics", label: "Métricas principales", selector: "#dashboard-metrics-grid", kind: "card", position: "main-upper", interactive: false, description: "Grilla de cuatro KPI del día." },
      { element_id: "dashboard-orders", label: "Pedidos recientes", selector: "#dashboard-recent-orders", kind: "list", position: "main-bottom", interactive: false, description: "Tarjeta grande con historial corto de pedidos." },
    ],
    demo_steps: [
      { step: 1, title: "Ubicar navegación", description: "Señalar que todas las secciones cuelgan del sidebar izquierdo.", focus_selectors: ["#nav-catalog", "#nav-finances", "#nav-disputes", "#nav-schedule", "#nav-support"] },
      { step: 2, title: "Leer indicadores", description: "Explicar el bloque de KPI del centro superior.", focus_selectors: ["#dashboard-metrics-grid"] },
      { step: 3, title: "Mostrar operación en vivo", description: "Usar el botón Simular Pedido para ilustrar una alerta operativa.", focus_selectors: ["#dashboard-simulate-order-btn"] },
    ],
    talking_points: [
      "Esta vista sirve para una lectura rápida del negocio antes de entrar al detalle.",
      "El sidebar izquierdo es estable y no cambia entre secciones autenticadas.",
      "El área inferior de pedidos recientes ayuda a conectar métricas con casos concretos.",
    ],
  },
  catalog: {
    current_view: "catalog",
    screen_title: "Catálogo",
    screen_goal: "Gestionar productos, complementos, precios, stock y estado de activación.",
    allowed_actions: ["edit_product", "toggle_product_status", "update_price", "update_stock", "add_product", "edit_topping"],
    required_fields: {
      edit_product: ["product_id"],
      update_price: ["product_id", "new_price"],
      update_stock: ["product_id", "new_stock"],
      toggle_product_status: ["product_id", "is_active"],
    },
    navigation_hints: [
      { section_id: "products-list", label: "Lista de Productos", selector: "#products-list", description: "Tarjeta principal con productos" },
      { section_id: "toppings-list", label: "Toppings", selector: "#toppings-list", description: "Tarjeta inferior con complementos" },
    ],
    data_available: ["products", "toppings", "categories"],
    layout_notes: "Header con CTA para agregar producto arriba a la derecha, buscador debajo y dos bloques principales: lista de productos y rejilla de toppings.",
    layout_regions: [
      { region_id: "catalog-header", label: "Encabezado", position: "main-top", description: "Título de la sección y botón Agregar Producto." },
      { region_id: "catalog-search", label: "Buscador", position: "main-top-left", description: "Input para filtrar por nombre o categoría." },
      { region_id: "catalog-products", label: "Productos", position: "main-middle", description: "Listado vertical de cards de producto con switch y botón de edición." },
      { region_id: "catalog-toppings", label: "Complementos", position: "main-bottom", description: "Grid de toppings con switch de activación." },
    ],
    key_elements: [
      { element_id: "catalog-add-product", label: "Agregar Producto", selector: "#catalog-add-product-btn", kind: "button", position: "main-top-right", interactive: true, description: "CTA rojo para abrir la creación de productos." },
      { element_id: "catalog-search-input", label: "Buscar productos", selector: "#catalog-search-input", kind: "input", position: "main-top-left", interactive: true, description: "Buscador con ícono de lupa a la izquierda." },
      { element_id: "catalog-products-list", label: "Productos", selector: "#products-list", kind: "list", position: "main-middle", interactive: false, description: "Tarjeta con productos, precio, stock, switch y botón de editar." },
      { element_id: "catalog-toppings-list", label: "Toppings", selector: "#toppings-list", kind: "list", position: "main-bottom", interactive: false, description: "Tarjeta con complementos en columnas." },
      { element_id: "catalog-edit-modal", label: "Modal Editar Producto", selector: "#catalog-edit-product-modal", kind: "modal", position: "center", interactive: true, description: "Modal con campos de nombre, precio y stock." },
    ],
    demo_steps: [
      { step: 1, title: "Explicar filtro", description: "Mostrar que el buscador reduce la lista de productos.", focus_selectors: ["#catalog-search-input", "#products-list"] },
      { step: 2, title: "Leer una fila de producto", description: "Resaltar que cada producto tiene precio, stock, switch y lápiz de edición.", focus_selectors: ["#products-list"] },
      { step: 3, title: "Cerrar con complementos", description: "Enseñar que los toppings se administran aparte en la parte inferior.", focus_selectors: ["#toppings-list"] },
    ],
    talking_points: [
      "La edición operativa está concentrada en una sola vista: búsqueda, productos y complementos.",
      "La acción principal está arriba a la derecha; la gestión cotidiana ocurre en la lista central.",
      "Los switches permiten hablar de activar o pausar disponibilidad sin salir del listado.",
    ],
  },
  finances: {
    current_view: "finances",
    screen_title: "Finanzas",
    screen_goal: "Consultar pagos, montos pendientes y evolución de dispersión.",
    allowed_actions: ["view_payment_details", "download_report", "filter_payments"],
    required_fields: {
      view_payment_details: ["payment_id"],
      filter_payments: ["date_from", "date_to"],
    },
    navigation_hints: [
      { section_id: "balance-summary", label: "Resumen", selector: "#balance-summary", description: "Tarjetas superiores de balance" },
      { section_id: "payments-table", label: "Tabla de Pagos", selector: "#payments-table", description: "Historial de dispersiones" },
    ],
    data_available: ["payments", "balance", "pending_amount", "last_payment_date"],
    layout_notes: "Header con botón Descargar Reporte arriba a la derecha, tres tarjetas resumen, luego una barra visual de balance y abajo una tabla de pagos.",
    layout_regions: [
      { region_id: "finances-header", label: "Encabezado", position: "main-top", description: "Título y CTA de descarga." },
      { region_id: "finances-summary", label: "Resumen financiero", position: "main-upper", description: "Tres tarjetas con total recibido, por dispersar y próximo pago." },
      { region_id: "finances-balance", label: "Balance del mes", position: "main-middle", description: "Tarjeta con barra de progreso entre pagado y pendiente." },
      { region_id: "finances-table", label: "Historial", position: "main-bottom", description: "Tabla con fecha, orden, descripción, valor y estado." },
    ],
    key_elements: [
      { element_id: "finances-download", label: "Descargar Reporte", selector: "#finances-download-report-btn", kind: "button", position: "main-top-right", interactive: true, description: "Botón outline para exportar el reporte." },
      { element_id: "finances-summary-cards", label: "Resumen", selector: "#balance-summary", kind: "card", position: "main-upper", interactive: false, description: "Grilla de tres indicadores financieros." },
      { element_id: "finances-month-balance", label: "Balance del Mes", selector: "#finances-monthly-balance-card", kind: "card", position: "main-middle", interactive: false, description: "Tarjeta con barra horizontal de progreso." },
      { element_id: "finances-payments-table", label: "Historial de Pagos", selector: "#payments-table", kind: "table", position: "main-bottom", interactive: false, description: "Tabla principal con dispersión por orden." },
    ],
    demo_steps: [
      { step: 1, title: "Explicar el resumen", description: "Leer de arriba hacia abajo: recibido, pendiente y próximo pago.", focus_selectors: ["#balance-summary"] },
      { step: 2, title: "Mostrar proporción", description: "Usar la tarjeta Balance del Mes para explicar cuánto ya fue dispersado.", focus_selectors: ["#finances-monthly-balance-card"] },
      { step: 3, title: "Ir al detalle", description: "Bajar a la tabla para ver pagos concretos.", focus_selectors: ["#payments-table"] },
    ],
    talking_points: [
      "La lectura recomendada es resumen arriba y detalle abajo.",
      "El botón de descarga vive en la esquina superior derecha del header.",
      "La tabla inferior aterriza los números del resumen en órdenes específicas.",
    ],
  },
  disputes: {
    current_view: "disputes",
    screen_title: "Disputas",
    screen_goal: "Crear reclamaciones nuevas y consultar el estado de disputas activas o cerradas.",
    allowed_actions: ["create_dispute", "view_dispute", "add_evidence", "cancel_dispute"],
    required_fields: {
      create_dispute: ["order_id", "reason", "description"],
      view_dispute: ["dispute_id"],
      add_evidence: ["dispute_id", "evidence_type", "content"],
    },
    navigation_hints: [
      { section_id: "new-dispute-btn", label: "Nueva Disputa", selector: "#new-dispute-btn", description: "CTA principal del header" },
      { section_id: "disputes-list", label: "Lista de Disputas", selector: "#disputes-list", description: "Tarjeta con disputas activas" },
    ],
    data_available: ["disputes", "dispute_reasons", "open_disputes_count"],
    layout_notes: "Header con CTA roja arriba a la derecha, tarjetas de resumen por estado, lista de disputas activas en el centro y un historial abajo si existe.",
    layout_regions: [
      { region_id: "disputes-header", label: "Encabezado", position: "main-top", description: "Título y botón Nueva Disputa." },
      { region_id: "disputes-summary", label: "Resumen por estado", position: "main-upper", description: "Tres cards: abiertas, en revisión y resueltas." },
      { region_id: "disputes-active", label: "Disputas activas", position: "main-middle", description: "Listado vertical con badge de estado y botón Ver." },
      { region_id: "disputes-history", label: "Historial", position: "main-bottom", description: "Listado de disputas cerradas, si existen." },
    ],
    key_elements: [
      { element_id: "disputes-new", label: "Nueva Disputa", selector: "#new-dispute-btn", kind: "button", position: "main-top-right", interactive: true, description: "CTA rojo para abrir el modal de creación." },
      { element_id: "disputes-list-active", label: "Disputas activas", selector: "#disputes-list", kind: "list", position: "main-middle", interactive: false, description: "Tarjeta principal con las reclamaciones abiertas o en revisión." },
      { element_id: "disputes-create-modal", label: "Modal Nueva Disputa", selector: "#dispute-create-modal", kind: "modal", position: "center", interactive: true, description: "Modal con orden, motivo y descripción." },
      { element_id: "disputes-order-field", label: "ID de la Orden", selector: "#dispute-order-id", kind: "input", position: "center", interactive: true, description: "Primer campo del modal de creación." },
      { element_id: "disputes-description-field", label: "Descripción", selector: "#dispute-description", kind: "input", position: "center", interactive: true, description: "Área de texto amplia para explicar el problema." },
    ],
    demo_steps: [
      { step: 1, title: "Ubicar CTA", description: "Mostrar que la creación de disputas empieza en el botón rojo del header.", focus_selectors: ["#new-dispute-btn"] },
      { step: 2, title: "Leer estados", description: "Explicar las tarjetas que resumen abiertas, en revisión y resueltas.", focus_selectors: ["#disputes-list"] },
      { step: 3, title: "Explicar modal", description: "Si se abre el modal, presentar el orden, motivo y descripción como datos requeridos.", focus_selectors: ["#dispute-order-id", "#dispute-description"] },
    ],
    talking_points: [
      "La prioridad visual es el CTA de creación, arriba a la derecha.",
      "La lista central sirve para revisar en qué estado va cada reclamación.",
      "El modal de alta obliga a definir orden, motivo y descripción antes de crear.",
    ],
  },
  schedule: {
    current_view: "schedule",
    screen_title: "Horarios",
    screen_goal: "Configurar días de apertura, horas de operación y aplicar cambios rápidos.",
    allowed_actions: ["update_schedule", "toggle_day", "set_hours"],
    required_fields: {
      update_schedule: ["day", "is_open", "open_time", "close_time"],
      toggle_day: ["day", "is_open"],
      set_hours: ["day", "open_time", "close_time"],
    },
    navigation_hints: [
      { section_id: "schedule-grid", label: "Horarios", selector: "#schedule-grid", description: "Grilla principal del horario semanal" },
    ],
    data_available: ["weekly_schedule", "special_hours"],
    layout_notes: "Header con botones de guardar o descartar solo cuando hay cambios, tarjeta central con un renglón por día y bloque inferior con acciones rápidas.",
    layout_regions: [
      { region_id: "schedule-header", label: "Encabezado", position: "main-top", description: "Título y botones de guardar/descartar en el extremo derecho cuando aplica." },
      { region_id: "schedule-grid-region", label: "Horario semanal", position: "main-middle", description: "Tarjeta con filas por día, switch y campos de hora." },
      { region_id: "schedule-actions", label: "Acciones rápidas", position: "main-lower", description: "Botones secundarios para aplicar configuraciones masivas." },
      { region_id: "schedule-note", label: "Nota operativa", position: "main-bottom", description: "Tarjeta informativa sobre tiempo de propagación de cambios." },
    ],
    key_elements: [
      { element_id: "schedule-grid-card", label: "Horario Semanal", selector: "#schedule-grid", kind: "card", position: "main-middle", interactive: false, description: "Tarjeta principal con una fila por día." },
      { element_id: "schedule-save", label: "Guardar Cambios", selector: "#schedule-save-btn", kind: "button", position: "main-top-right", interactive: true, description: "CTA rojo visible solo cuando hay cambios pendientes." },
      { element_id: "schedule-discard", label: "Descartar", selector: "#schedule-discard-btn", kind: "button", position: "main-top-right", interactive: true, description: "Botón outline junto al de guardar." },
      { element_id: "schedule-open-all", label: "Abrir todos los días", selector: "#schedule-open-all-btn", kind: "button", position: "main-lower-left", interactive: true, description: "Acción rápida para marcar toda la semana como abierta." },
      { element_id: "schedule-standard-hours", label: "Horario estándar", selector: "#schedule-standard-hours-btn", kind: "button", position: "main-lower-left", interactive: true, description: "Acción rápida para fijar 10am a 10pm." },
    ],
    demo_steps: [
      { step: 1, title: "Explicar una fila", description: "Mostrar que cada día tiene switch y horas de apertura/cierre.", focus_selectors: ["#schedule-grid"] },
      { step: 2, title: "Mostrar acciones rápidas", description: "Bajar al bloque inferior para enseñar plantillas de horario.", focus_selectors: ["#schedule-open-all-btn", "#schedule-standard-hours-btn"] },
      { step: 3, title: "Cerrar con guardado", description: "Aclarar que los cambios se confirman arriba a la derecha cuando aparecen los botones.", focus_selectors: ["#schedule-save-btn"] },
    ],
    talking_points: [
      "El corazón de la pantalla es la fila por día dentro de la tarjeta central.",
      "Los botones de guardado aparecen condicionalmente, arriba a la derecha.",
      "Las acciones rápidas ahorran tiempo cuando el horario se repite toda la semana.",
    ],
  },
  support: {
    current_view: "support",
    screen_title: "Soporte",
    screen_goal: "Ofrecer canales de ayuda, preguntas frecuentes y acceso al chat.",
    allowed_actions: ["search_faq", "start_chat", "submit_ticket"],
    required_fields: {
      search_faq: ["query"],
      submit_ticket: ["subject", "description", "priority"],
    },
    navigation_hints: [
      { section_id: "faq-section", label: "FAQ", selector: "#faq-section", description: "Sección principal de preguntas frecuentes" },
      { section_id: "chat-btn", label: "Chat", selector: "#chat-btn", description: "Botón en el header" },
    ],
    data_available: ["faq_items", "ticket_history"],
    layout_notes: "Header con botón Chat con Soporte arriba a la derecha, tres tarjetas de contacto, bloque FAQ con buscador y un bloque final de recursos útiles.",
    layout_regions: [
      { region_id: "support-header", label: "Encabezado", position: "main-top", description: "Título de la sección y CTA de chat." },
      { region_id: "support-contact", label: "Canales de contacto", position: "main-upper", description: "Tres tarjetas: teléfono, email y chat." },
      { region_id: "support-faq", label: "Preguntas frecuentes", position: "main-middle", description: "Tarjeta con buscador y acordeón de respuestas." },
      { region_id: "support-resources", label: "Recursos útiles", position: "main-bottom", description: "Grid de enlaces secundarios." },
    ],
    key_elements: [
      { element_id: "support-chat", label: "Chat con Soporte", selector: "#chat-btn", kind: "button", position: "main-top-right", interactive: true, description: "CTA rojo para abrir el modal simulado de chat." },
      { element_id: "support-faq-section", label: "Preguntas Frecuentes", selector: "#faq-section", kind: "card", position: "main-middle", interactive: false, description: "Tarjeta principal con búsqueda y acordeón." },
      { element_id: "support-faq-search", label: "Buscar en FAQ", selector: "#support-faq-search-input", kind: "input", position: "main-middle-top", interactive: true, description: "Input con ícono de lupa dentro de la tarjeta FAQ." },
      { element_id: "support-chat-modal", label: "Modal de chat", selector: "#support-chat-modal", kind: "modal", position: "center", interactive: true, description: "Ventana modal centrada cuando se abre el chat." },
    ],
    demo_steps: [
      { step: 1, title: "Mostrar canal directo", description: "Señalar el botón Chat con Soporte arriba a la derecha.", focus_selectors: ["#chat-btn"] },
      { step: 2, title: "Explicar autoservicio", description: "Bajar a FAQ y usar el buscador como punto de entrada.", focus_selectors: ["#faq-section", "#support-faq-search-input"] },
      { step: 3, title: "Cerrar con recursos", description: "Mencionar que debajo hay enlaces a guías y políticas.", focus_selectors: [] },
    ],
    talking_points: [
      "La pantalla combina soporte asistido y autoservicio.",
      "El CTA más visible es el chat, arriba a la derecha.",
      "La tarjeta FAQ ocupa el centro de la pantalla y es el mejor lugar para dudas frecuentes.",
    ],
  },
}

// Available tools for AI agents
export const aiTools: AITool[] = [
  {
    name: "query_catalog",
    description: "Consultar el catálogo de productos del aliado",
    parameters: {
      category: { type: "string", required: false, description: "Filtrar por categoría" },
      active_only: { type: "boolean", required: false, description: "Solo productos activos" },
    },
  },
  {
    name: "update_price",
    description: "Actualizar el precio de un producto",
    parameters: {
      product_id: { type: "string", required: true, description: "ID del producto" },
      new_price: { type: "number", required: true, description: "Nuevo precio en centavos" },
    },
  },
  {
    name: "update_stock",
    description: "Actualizar el stock de un producto",
    parameters: {
      product_id: { type: "string", required: true, description: "ID del producto" },
      new_stock: { type: "number", required: true, description: "Nueva cantidad en stock" },
    },
  },
  {
    name: "toggle_product",
    description: "Activar o desactivar un producto",
    parameters: {
      product_id: { type: "string", required: true, description: "ID del producto" },
      is_active: { type: "boolean", required: true, description: "Estado de activación" },
    },
  },
  {
    name: "query_payments",
    description: "Consultar historial de pagos",
    parameters: {
      date_from: { type: "string", required: false, description: "Fecha inicial (YYYY-MM-DD)" },
      date_to: { type: "string", required: false, description: "Fecha final (YYYY-MM-DD)" },
      status: { type: "string", required: false, description: "Filtrar por estado" },
    },
  },
  {
    name: "create_dispute",
    description: "Crear una nueva disputa",
    parameters: {
      order_id: { type: "string", required: true, description: "ID de la orden" },
      reason: { type: "string", required: true, description: "Motivo de la disputa" },
      description: { type: "string", required: true, description: "Descripción detallada" },
    },
  },
  {
    name: "update_schedule",
    description: "Actualizar horarios de operación",
    parameters: {
      day: { type: "string", required: true, description: "Día de la semana" },
      is_open: { type: "boolean", required: true, description: "Si está abierto" },
      open_time: { type: "string", required: false, description: "Hora de apertura (HH:MM)" },
      close_time: { type: "string", required: false, description: "Hora de cierre (HH:MM)" },
    },
  },
  {
    name: "navigate_to",
    description: "Navegar a una sección específica",
    parameters: {
      section_id: { type: "string", required: true, description: "ID de la sección destino" },
    },
  },
]

// Generate full context payload
export function generateAIContextPayload(
  section: string,
  userContext: ScreenContext["user_context"],
  activeTool: string | null = null,
  lastAction: string | null = null
): AIContextPayload {
  const baseContext = screenContexts[section] || screenContexts.dashboard

  return {
    screen: {
      ...baseContext,
      current_path: buildPath(section in screenContexts ? section : "dashboard"),
      user_context: userContext,
      timestamp: new Date().toISOString(),
    },
    available_tools: aiTools,
    active_tool: activeTool,
    last_action: lastAction,
    navigation_function: "window.navigateToSection(sectionId)",
  }
}
