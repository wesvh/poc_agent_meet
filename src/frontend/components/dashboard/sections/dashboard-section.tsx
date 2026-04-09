"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { mockMetrics, mockOrders, type Order } from "@/lib/mock-data"
import {
  DollarSign,
  ShoppingBag,
  Clock,
  Star,
  TrendingUp,
  AlertCircle,
  Bell,
  CheckCircle,
  Package,
} from "lucide-react"
import { cn } from "@/lib/utils"

export function DashboardSection() {
  const [orders, setOrders] = useState<Order[]>(mockOrders)
  const [notification, setNotification] = useState<Order | null>(null)

  const simulateNewOrder = () => {
    const newOrder: Order = {
      id: `ORD-2024-${Math.floor(Math.random() * 1000)}`,
      customerName: ["Ana M.", "Luis R.", "Sofia T.", "Carlos P."][Math.floor(Math.random() * 4)],
      items: ["Pizza Margherita", "Lasagna Clásica", "Tiramisu"].slice(0, Math.floor(Math.random() * 2) + 1),
      total: Math.floor(Math.random() * 50000) + 25000,
      status: "pending",
      timestamp: new Date().toISOString(),
    }
    
    setNotification(newOrder)
    setOrders((prev) => [newOrder, ...prev.slice(0, 4)])
    
    setTimeout(() => setNotification(null), 5000)
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(value)
  }

  const getStatusColor = (status: Order["status"]) => {
    switch (status) {
      case "pending": return "bg-yellow-100 text-yellow-700"
      case "preparing": return "bg-blue-100 text-blue-700"
      case "ready": return "bg-green-100 text-green-700"
      case "delivered": return "bg-gray-100 text-gray-700"
    }
  }

  const getStatusLabel = (status: Order["status"]) => {
    switch (status) {
      case "pending": return "Pendiente"
      case "preparing": return "Preparando"
      case "ready": return "Listo"
      case "delivered": return "Entregado"
    }
  }

  return (
    <div className="space-y-6">
      {/* Notification Toast */}
      {notification && (
        <div className="fixed right-4 top-4 z-50 animate-in slide-in-from-right">
          <Card className="w-80 border-[#FF4940] shadow-lg">
            <CardContent className="flex items-start gap-3 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#FF4940]">
                <Bell className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-foreground">Nuevo Pedido</p>
                <p className="text-sm text-muted-foreground">{notification.id}</p>
                <p className="text-sm font-medium text-[#FF4940]">{formatCurrency(notification.total)}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">Resumen de tu negocio hoy</p>
        </div>
        <Button
          id="dashboard-simulate-order-btn"
          onClick={simulateNewOrder}
          className="bg-[#FF4940] text-white hover:bg-[#E63E36]"
        >
          <Bell className="mr-2 h-4 w-4" />
          Simular Pedido
        </Button>
      </div>

      {/* Metrics Grid */}
      <div id="dashboard-metrics-grid" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#FFF5F5]">
              <DollarSign className="h-6 w-6 text-[#FF4940]" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Ventas Hoy</p>
              <p className="text-2xl font-bold text-foreground">{formatCurrency(mockMetrics.salesToday)}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50">
              <ShoppingBag className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Pedidos Hoy</p>
              <p className="text-2xl font-bold text-foreground">{mockMetrics.ordersToday}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-yellow-50">
              <Clock className="h-6 w-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Pedidos Activos</p>
              <p className="text-2xl font-bold text-foreground">{mockMetrics.activeOrders}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-50">
              <Star className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Calificación</p>
              <p className="text-2xl font-bold text-foreground">{mockMetrics.averageRating}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Secondary Metrics */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="flex items-center justify-between p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
                <TrendingUp className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Crecimiento Semanal</p>
                <p className="text-lg font-semibold text-foreground">+{mockMetrics.weeklyGrowth}%</p>
              </div>
            </div>
            <CheckCircle className="h-5 w-5 text-green-500" />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-100">
                <AlertCircle className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Disputas Pendientes</p>
                <p className="text-lg font-semibold text-foreground">{mockMetrics.pendingDisputes}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Orders */}
      <Card id="dashboard-recent-orders">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Pedidos Recientes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {orders.map((order) => (
              <div
                key={order.id}
                className="flex items-center justify-between rounded-lg border border-border p-4 transition-all hover:bg-muted/50"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                    <ShoppingBag className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-medium text-foreground">{order.id}</p>
                    <p className="text-sm text-muted-foreground">
                      {order.customerName} - {order.items.join(", ")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className={cn("rounded-full px-3 py-1 text-xs font-medium", getStatusColor(order.status))}>
                    {getStatusLabel(order.status)}
                  </span>
                  <span className="font-semibold text-foreground">{formatCurrency(order.total)}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
