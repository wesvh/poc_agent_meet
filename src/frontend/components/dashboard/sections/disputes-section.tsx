"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Field, FieldLabel } from "@/components/ui/field"
import { mockDisputes, type Dispute } from "@/lib/mock-data"
import {
  MessageSquareWarning,
  Plus,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
} from "lucide-react"
import { cn } from "@/lib/utils"

const disputeReasons = [
  "Orden incompleta",
  "Cobro indebido",
  "Producto dañado",
  "Demora en entrega",
  "Error en facturación",
  "Otro",
]

export function DisputesSection() {
  const [disputes, setDisputes] = useState<Dispute[]>(mockDisputes)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedDispute, setSelectedDispute] = useState<Dispute | null>(null)
  const [newDispute, setNewDispute] = useState({
    orderId: "",
    reason: "",
    description: "",
  })

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

  const getStatusIcon = (status: Dispute["status"]) => {
    switch (status) {
      case "open":
        return <AlertCircle className="h-4 w-4 text-yellow-600" />
      case "in_review":
        return <Clock className="h-4 w-4 text-blue-600" />
      case "resolved":
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case "rejected":
        return <XCircle className="h-4 w-4 text-red-600" />
    }
  }

  const getStatusStyle = (status: Dispute["status"]) => {
    switch (status) {
      case "open":
        return "bg-yellow-100 text-yellow-700"
      case "in_review":
        return "bg-blue-100 text-blue-700"
      case "resolved":
        return "bg-green-100 text-green-700"
      case "rejected":
        return "bg-red-100 text-red-700"
    }
  }

  const getStatusLabel = (status: Dispute["status"]) => {
    switch (status) {
      case "open":
        return "Abierta"
      case "in_review":
        return "En Revisión"
      case "resolved":
        return "Resuelta"
      case "rejected":
        return "Rechazada"
    }
  }

  const handleCreateDispute = () => {
    const dispute: Dispute = {
      id: `disp_${Date.now()}`,
      orderId: newDispute.orderId,
      date: new Date().toISOString().split("T")[0],
      reason: newDispute.reason,
      description: newDispute.description,
      status: "open",
      amount: Math.floor(Math.random() * 50000) + 10000,
    }
    setDisputes((prev) => [dispute, ...prev])
    setNewDispute({ orderId: "", reason: "", description: "" })
    setIsCreateOpen(false)
  }

  const openDisputes = disputes.filter((d) => d.status === "open" || d.status === "in_review")
  const closedDisputes = disputes.filter((d) => d.status === "resolved" || d.status === "rejected")

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Disputas</h1>
          <p className="text-muted-foreground">Gestiona tus reclamaciones</p>
        </div>
        <Button
          id="new-dispute-btn"
          onClick={() => setIsCreateOpen(true)}
          className="bg-[#FF4940] text-white hover:bg-[#E63E36]"
        >
          <Plus className="mr-2 h-4 w-4" />
          Nueva Disputa
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-100">
              <AlertCircle className="h-5 w-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Abiertas</p>
              <p className="text-xl font-bold text-foreground">
                {disputes.filter((d) => d.status === "open").length}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
              <Clock className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">En Revisión</p>
              <p className="text-xl font-bold text-foreground">
                {disputes.filter((d) => d.status === "in_review").length}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Resueltas</p>
              <p className="text-xl font-bold text-foreground">
                {disputes.filter((d) => d.status === "resolved").length}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Disputes */}
      <Card id="disputes-list">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquareWarning className="h-5 w-5" />
            Disputas Activas ({openDisputes.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {openDisputes.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">
              No hay disputas activas
            </p>
          ) : (
            <div className="space-y-3">
              {openDisputes.map((dispute) => (
                <div
                  key={dispute.id}
                  className="flex items-center justify-between rounded-lg border border-border p-4 transition-all hover:bg-muted/50"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-foreground">{dispute.orderId}</p>
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                          getStatusStyle(dispute.status)
                        )}
                      >
                        {getStatusIcon(dispute.status)}
                        {getStatusLabel(dispute.status)}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">{dispute.reason}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(dispute.date)} | Monto: {formatCurrency(dispute.amount)}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedDispute(dispute)}
                  >
                    <Eye className="mr-1 h-4 w-4" />
                    Ver
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Closed Disputes */}
      {closedDisputes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Historial de Disputas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {closedDisputes.map((dispute) => (
                <div
                  key={dispute.id}
                  className="flex items-center justify-between rounded-lg border border-border p-4 opacity-70"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-foreground">{dispute.orderId}</p>
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                          getStatusStyle(dispute.status)
                        )}
                      >
                        {getStatusIcon(dispute.status)}
                        {getStatusLabel(dispute.status)}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">{dispute.reason}</p>
                  </div>
                  <span className="text-sm text-muted-foreground">{formatDate(dispute.date)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create Dispute Modal */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent id="dispute-create-modal">
          <DialogHeader>
            <DialogTitle>Nueva Disputa</DialogTitle>
            <DialogDescription>
              Crea una nueva reclamación para revisar un problema con una orden
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <Field>
              <FieldLabel>ID de la Orden</FieldLabel>
              <Input
                id="dispute-order-id"
                placeholder="ORD-2024-XXX"
                value={newDispute.orderId}
                onChange={(e) =>
                  setNewDispute((prev) => ({ ...prev, orderId: e.target.value }))
                }
              />
            </Field>
            <Field>
              <FieldLabel>Motivo</FieldLabel>
              <Select
                value={newDispute.reason}
                onValueChange={(value) =>
                  setNewDispute((prev) => ({ ...prev, reason: value }))
                }
              >
                <SelectTrigger id="dispute-reason">
                  <SelectValue placeholder="Selecciona un motivo" />
                </SelectTrigger>
                <SelectContent>
                  {disputeReasons.map((reason) => (
                    <SelectItem key={reason} value={reason}>
                      {reason}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>Descripción</FieldLabel>
              <Textarea
                id="dispute-description"
                placeholder="Describe el problema con el mayor detalle posible..."
                rows={4}
                value={newDispute.description}
                onChange={(e) =>
                  setNewDispute((prev) => ({ ...prev, description: e.target.value }))
                }
              />
            </Field>
          </div>
          <DialogFooter>
            <Button id="dispute-cancel-btn" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancelar
            </Button>
            <Button
              id="dispute-submit-btn"
              onClick={handleCreateDispute}
              disabled={!newDispute.orderId || !newDispute.reason}
              className="bg-[#FF4940] text-white hover:bg-[#E63E36]"
            >
              Crear Disputa
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Dispute Modal */}
      <Dialog open={!!selectedDispute} onOpenChange={() => setSelectedDispute(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Detalle de Disputa</DialogTitle>
          </DialogHeader>
          {selectedDispute && (
            <div className="space-y-4 py-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">ID Orden</p>
                  <p className="font-medium text-foreground">{selectedDispute.orderId}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Fecha</p>
                  <p className="font-medium text-foreground">{formatDate(selectedDispute.date)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Motivo</p>
                  <p className="font-medium text-foreground">{selectedDispute.reason}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Monto en Disputa</p>
                  <p className="font-medium text-foreground">{formatCurrency(selectedDispute.amount)}</p>
                </div>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Descripción</p>
                <p className="mt-1 rounded-lg bg-muted p-3 text-sm text-foreground">
                  {selectedDispute.description}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Estado:</span>
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium",
                    getStatusStyle(selectedDispute.status)
                  )}
                >
                  {getStatusIcon(selectedDispute.status)}
                  {getStatusLabel(selectedDispute.status)}
                </span>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedDispute(null)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
