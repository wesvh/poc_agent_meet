"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { mockPayments, type PaymentRecord } from "@/lib/mock-data"
import {
  Wallet,
  Download,
  Clock,
  CheckCircle,
  AlertCircle,
  Calendar,
  TrendingUp,
  ArrowUpRight,
} from "lucide-react"
import { cn } from "@/lib/utils"

export function FinancesSection() {
  const [payments] = useState<PaymentRecord[]>(mockPayments)

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("es-CO", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  const totalPaid = payments
    .filter((p) => p.status === "paid")
    .reduce((sum, p) => sum + p.netValue, 0)

  const totalPending = payments
    .filter((p) => p.status !== "paid")
    .reduce((sum, p) => sum + p.netValue, 0)

  const getStatusIcon = (status: PaymentRecord["status"]) => {
    switch (status) {
      case "paid":
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-600" />
      case "processing":
        return <AlertCircle className="h-4 w-4 text-blue-600" />
    }
  }

  const getStatusStyle = (status: PaymentRecord["status"]) => {
    switch (status) {
      case "paid":
        return "bg-green-100 text-green-700"
      case "pending":
        return "bg-yellow-100 text-yellow-700"
      case "processing":
        return "bg-blue-100 text-blue-700"
    }
  }

  const getStatusLabel = (status: PaymentRecord["status"]) => {
    switch (status) {
      case "paid":
        return "Pagado"
      case "pending":
        return "Pendiente"
      case "processing":
        return "Procesando"
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Finanzas</h1>
          <p className="text-muted-foreground">Historial de pagos y dispersiones</p>
        </div>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Descargar Reporte
        </Button>
      </div>

      {/* Balance Summary */}
      <div id="balance-summary" className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-100">
                <Wallet className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Recibido</p>
                <p className="text-2xl font-bold text-foreground">{formatCurrency(totalPaid)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-yellow-100">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Por Dispersar</p>
                <p className="text-2xl font-bold text-foreground">{formatCurrency(totalPending)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#FFF5F5]">
                <TrendingUp className="h-6 w-6 text-[#FF4940]" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Próximo Pago</p>
                <p className="text-lg font-bold text-foreground">Martes, Ene 30</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Visual Balance */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ArrowUpRight className="h-5 w-5" />
            Balance del Mes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Progreso de dispersión</span>
              <span className="font-medium text-foreground">
                {Math.round((totalPaid / (totalPaid + totalPending)) * 100)}%
              </span>
            </div>
            <div className="h-4 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-[#FF4940] transition-all"
                style={{ width: `${(totalPaid / (totalPaid + totalPending)) * 100}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Pagado: {formatCurrency(totalPaid)}</span>
              <span>Pendiente: {formatCurrency(totalPending)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Payments Table */}
      <Card id="payments-table">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Historial de Pagos
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left text-sm text-muted-foreground">
                  <th className="pb-3 font-medium">Fecha</th>
                  <th className="pb-3 font-medium">ID Orden</th>
                  <th className="pb-3 font-medium">Descripción</th>
                  <th className="pb-3 font-medium">Valor Neto</th>
                  <th className="pb-3 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((payment) => (
                  <tr key={payment.id} className="border-b border-border last:border-0">
                    <td className="py-4 text-sm text-foreground">{formatDate(payment.date)}</td>
                    <td className="py-4 text-sm font-mono text-muted-foreground">{payment.orderId}</td>
                    <td className="py-4 text-sm text-foreground">{payment.description}</td>
                    <td className="py-4 text-sm font-semibold text-foreground">
                      {formatCurrency(payment.netValue)}
                    </td>
                    <td className="py-4">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
                          getStatusStyle(payment.status)
                        )}
                      >
                        {getStatusIcon(payment.status)}
                        {getStatusLabel(payment.status)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
