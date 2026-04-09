// Mock data for Portal Partners

export interface Product {
  id: string
  name: string
  description: string
  price: number
  category: string
  image: string
  isActive: boolean
  stock: number
}

export interface Topping {
  id: string
  name: string
  price: number
  isActive: boolean
}

export interface PaymentRecord {
  id: string
  date: string
  orderId: string
  netValue: number
  status: "paid" | "pending" | "processing"
  description: string
}

export interface Dispute {
  id: string
  orderId: string
  date: string
  reason: string
  description: string
  status: "open" | "in_review" | "resolved" | "rejected"
  amount: number
}

export interface Schedule {
  day: string
  isOpen: boolean
  openTime: string
  closeTime: string
}

export interface Order {
  id: string
  customerName: string
  items: string[]
  total: number
  status: "pending" | "preparing" | "ready" | "delivered"
  timestamp: string
}

// Products Mock Data
export const mockProducts: Product[] = [
  {
    id: "prod_001",
    name: "Pizza Margherita",
    description: "Tomate, mozzarella, albahaca fresca",
    price: 28500,
    category: "Pizzas",
    image: "/placeholder.svg?height=100&width=100",
    isActive: true,
    stock: 50,
  },
  {
    id: "prod_002",
    name: "Pizza Pepperoni",
    description: "Pepperoni, mozzarella, salsa de tomate",
    price: 32000,
    category: "Pizzas",
    image: "/placeholder.svg?height=100&width=100",
    isActive: true,
    stock: 45,
  },
  {
    id: "prod_003",
    name: "Pizza Quattro Formaggi",
    description: "Mozzarella, gorgonzola, parmesano, provolone",
    price: 35000,
    category: "Pizzas",
    image: "/placeholder.svg?height=100&width=100",
    isActive: true,
    stock: 30,
  },
  {
    id: "prod_004",
    name: "Lasagna Clásica",
    description: "Carne molida, bechamel, pasta fresca",
    price: 29500,
    category: "Pastas",
    image: "/placeholder.svg?height=100&width=100",
    isActive: true,
    stock: 20,
  },
  {
    id: "prod_005",
    name: "Tiramisu",
    description: "Postre italiano con café y mascarpone",
    price: 15000,
    category: "Postres",
    image: "/placeholder.svg?height=100&width=100",
    isActive: false,
    stock: 0,
  },
]

// Toppings Mock Data
export const mockToppings: Topping[] = [
  { id: "top_001", name: "Queso Extra", price: 4500, isActive: true },
  { id: "top_002", name: "Pepperoni Extra", price: 5000, isActive: true },
  { id: "top_003", name: "Champiñones", price: 3500, isActive: true },
  { id: "top_004", name: "Aceitunas", price: 3000, isActive: true },
  { id: "top_005", name: "Jalapeños", price: 2500, isActive: false },
]

// Payment Records Mock Data
export const mockPayments: PaymentRecord[] = [
  {
    id: "pay_001",
    date: "2024-01-15",
    orderId: "ORD-2024-001",
    netValue: 125000,
    status: "paid",
    description: "Dispersión semanal",
  },
  {
    id: "pay_002",
    date: "2024-01-08",
    orderId: "ORD-2024-002",
    netValue: 98500,
    status: "paid",
    description: "Dispersión semanal",
  },
  {
    id: "pay_003",
    date: "2024-01-22",
    orderId: "ORD-2024-003",
    netValue: 156000,
    status: "pending",
    description: "Dispersión en proceso",
  },
  {
    id: "pay_004",
    date: "2024-01-29",
    orderId: "ORD-2024-004",
    netValue: 87000,
    status: "processing",
    description: "Validación bancaria",
  },
]

// Disputes Mock Data
export const mockDisputes: Dispute[] = [
  {
    id: "disp_001",
    orderId: "ORD-2024-156",
    date: "2024-01-20",
    reason: "Orden incompleta",
    description: "El cliente reporta que faltó una pizza del pedido",
    status: "open",
    amount: 32000,
  },
  {
    id: "disp_002",
    orderId: "ORD-2024-142",
    date: "2024-01-18",
    reason: "Cobro indebido",
    description: "Se cobró doble comisión en esta orden",
    status: "in_review",
    amount: 8500,
  },
  {
    id: "disp_003",
    orderId: "ORD-2024-098",
    date: "2024-01-10",
    reason: "Producto dañado",
    description: "La pizza llegó en mal estado según foto del cliente",
    status: "resolved",
    amount: 28500,
  },
]

// Schedule Mock Data
export const mockSchedule: Schedule[] = [
  { day: "Lunes", isOpen: true, openTime: "11:00", closeTime: "22:00" },
  { day: "Martes", isOpen: true, openTime: "11:00", closeTime: "22:00" },
  { day: "Miércoles", isOpen: true, openTime: "11:00", closeTime: "22:00" },
  { day: "Jueves", isOpen: true, openTime: "11:00", closeTime: "23:00" },
  { day: "Viernes", isOpen: true, openTime: "11:00", closeTime: "23:30" },
  { day: "Sábado", isOpen: true, openTime: "12:00", closeTime: "23:30" },
  { day: "Domingo", isOpen: false, openTime: "12:00", closeTime: "21:00" },
]

// Recent Orders Mock Data
export const mockOrders: Order[] = [
  {
    id: "ORD-2024-201",
    customerName: "María G.",
    items: ["Pizza Margherita", "Coca-Cola"],
    total: 34500,
    status: "preparing",
    timestamp: "2024-01-25T14:30:00",
  },
  {
    id: "ORD-2024-202",
    customerName: "Juan P.",
    items: ["Pizza Pepperoni", "Pizza Quattro Formaggi"],
    total: 67000,
    status: "pending",
    timestamp: "2024-01-25T14:35:00",
  },
]

// Dashboard Metrics
export const mockMetrics = {
  salesToday: 485000,
  ordersToday: 18,
  activeOrders: 3,
  averageRating: 4.7,
  weeklyGrowth: 12.5,
  pendingDisputes: 2,
}

// FAQ Data
export const mockFAQ = [
  {
    question: "¿Cómo actualizo los precios de mis productos?",
    answer: "Ve a la sección de Catálogo, selecciona el producto y haz clic en Editar. Puedes modificar el precio y guardar los cambios.",
  },
  {
    question: "¿Cuándo recibo mis pagos?",
    answer: "Los pagos se dispersan semanalmente los días martes. Puedes ver el estado de tus pagos en la sección de Finanzas.",
  },
  {
    question: "¿Cómo creo una disputa?",
    answer: "En la sección de Disputas, haz clic en 'Nueva Disputa', selecciona el motivo y describe tu caso con el mayor detalle posible.",
  },
  {
    question: "¿Puedo pausar mi tienda temporalmente?",
    answer: "Sí, en la sección de Horarios puedes desactivar días específicos o contactar a soporte para pausar tu tienda completamente.",
  },
]
