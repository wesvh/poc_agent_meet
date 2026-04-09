// AI Context Protocol Types and Utilities
// This module provides the MCP-like interface for AI agents

export interface ScreenContext {
  current_view: string
  current_path: string
  user_context: {
    store_id: string | null
    store_name: string | null
    is_authenticated: boolean
  }
  allowed_actions: string[]
  required_fields: Record<string, string[]>
  navigation_hints: NavigationHint[]
  data_available: string[]
  timestamp: string
}

export interface NavigationHint {
  section_id: string
  label: string
  selector: string
  description: string
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

// Screen context configurations for each section
export const screenContexts: Record<string, Omit<ScreenContext, 'timestamp' | 'user_context' | 'current_path'>> = {
  dashboard: {
    current_view: "dashboard",
    allowed_actions: ["view_metrics", "navigate_to_section", "view_orders"],
    required_fields: {},
    navigation_hints: [
      { section_id: "catalog", label: "Catálogo", selector: "#nav-catalog", description: "Gestión de productos" },
      { section_id: "finances", label: "Finanzas", selector: "#nav-finances", description: "Pagos y dispersiones" },
      { section_id: "disputes", label: "Disputas", selector: "#nav-disputes", description: "Reclamaciones" },
      { section_id: "schedule", label: "Horarios", selector: "#nav-schedule", description: "Configuración de horarios" },
      { section_id: "support", label: "Soporte", selector: "#nav-support", description: "Centro de ayuda" },
    ],
    data_available: ["sales_today", "orders_today", "active_orders", "average_rating", "recent_orders"],
  },
  catalog: {
    current_view: "inventory",
    allowed_actions: ["edit_product", "toggle_product_status", "update_price", "update_stock", "add_product", "edit_topping"],
    required_fields: {
      edit_product: ["product_id"],
      update_price: ["product_id", "new_price"],
      update_stock: ["product_id", "new_stock"],
      toggle_product_status: ["product_id", "is_active"],
    },
    navigation_hints: [
      { section_id: "products-list", label: "Lista de Productos", selector: "#products-list", description: "Tabla de productos" },
      { section_id: "toppings-list", label: "Toppings", selector: "#toppings-list", description: "Complementos disponibles" },
    ],
    data_available: ["products", "toppings", "categories"],
  },
  finances: {
    current_view: "payments",
    allowed_actions: ["view_payment_details", "download_report", "filter_payments"],
    required_fields: {
      view_payment_details: ["payment_id"],
      filter_payments: ["date_from", "date_to"],
    },
    navigation_hints: [
      { section_id: "payments-table", label: "Tabla de Pagos", selector: "#payments-table", description: "Historial de dispersiones" },
      { section_id: "balance-summary", label: "Resumen", selector: "#balance-summary", description: "Balance actual" },
    ],
    data_available: ["payments", "balance", "pending_amount", "last_payment_date"],
  },
  disputes: {
    current_view: "disputes",
    allowed_actions: ["create_dispute", "view_dispute", "add_evidence", "cancel_dispute"],
    required_fields: {
      create_dispute: ["order_id", "reason", "description"],
      view_dispute: ["dispute_id"],
      add_evidence: ["dispute_id", "evidence_type", "content"],
    },
    navigation_hints: [
      { section_id: "disputes-list", label: "Lista de Disputas", selector: "#disputes-list", description: "Disputas activas" },
      { section_id: "new-dispute-btn", label: "Nueva Disputa", selector: "#new-dispute-btn", description: "Crear disputa" },
    ],
    data_available: ["disputes", "dispute_reasons", "open_disputes_count"],
  },
  schedule: {
    current_view: "schedule",
    allowed_actions: ["update_schedule", "toggle_day", "set_hours"],
    required_fields: {
      update_schedule: ["day", "is_open", "open_time", "close_time"],
      toggle_day: ["day", "is_open"],
      set_hours: ["day", "open_time", "close_time"],
    },
    navigation_hints: [
      { section_id: "schedule-grid", label: "Horarios", selector: "#schedule-grid", description: "Configuración semanal" },
    ],
    data_available: ["weekly_schedule", "special_hours"],
  },
  support: {
    current_view: "support",
    allowed_actions: ["search_faq", "start_chat", "submit_ticket"],
    required_fields: {
      search_faq: ["query"],
      submit_ticket: ["subject", "description", "priority"],
    },
    navigation_hints: [
      { section_id: "faq-section", label: "FAQ", selector: "#faq-section", description: "Preguntas frecuentes" },
      { section_id: "chat-btn", label: "Chat", selector: "#chat-btn", description: "Chat con soporte" },
    ],
    data_available: ["faq_items", "ticket_history"],
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
  userContext: ScreenContext['user_context'],
  activeTool: string | null = null,
  lastAction: string | null = null
): AIContextPayload {
  const baseContext = screenContexts[section] || screenContexts.dashboard
  
  return {
    screen: {
      ...baseContext,
      current_path: `/${section === 'dashboard' ? '' : section}`,
      user_context: userContext,
      timestamp: new Date().toISOString(),
    },
    available_tools: aiTools,
    active_tool: activeTool,
    last_action: lastAction,
    navigation_function: "window.navigateToSection(sectionId)",
  }
}
