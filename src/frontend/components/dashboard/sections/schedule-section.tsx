"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { mockSchedule, type Schedule } from "@/lib/mock-data"
import { Clock, Save, RotateCcw } from "lucide-react"
import { cn } from "@/lib/utils"

export function ScheduleSection() {
  const [schedule, setSchedule] = useState<Schedule[]>(mockSchedule)
  const [hasChanges, setHasChanges] = useState(false)
  const [highlightedDay, setHighlightedDay] = useState<string | null>(null)

  const toggleDay = (day: string) => {
    setSchedule((prev) =>
      prev.map((s) => (s.day === day ? { ...s, isOpen: !s.isOpen } : s))
    )
    setHasChanges(true)
    highlightElement(day)
  }

  const updateTime = (day: string, field: "openTime" | "closeTime", value: string) => {
    setSchedule((prev) =>
      prev.map((s) => (s.day === day ? { ...s, [field]: value } : s))
    )
    setHasChanges(true)
  }

  const saveChanges = () => {
    // In a real app, this would send to API
    setHasChanges(false)
  }

  const resetChanges = () => {
    setSchedule(mockSchedule)
    setHasChanges(false)
  }

  const highlightElement = (day: string) => {
    setHighlightedDay(day)
    setTimeout(() => setHighlightedDay(null), 2000)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Horarios</h1>
          <p className="text-muted-foreground">Configura tus días y horas de operación</p>
        </div>
        <div className="flex gap-2">
          {hasChanges && (
            <>
              <Button variant="outline" onClick={resetChanges}>
                <RotateCcw className="mr-2 h-4 w-4" />
                Descartar
              </Button>
              <Button
                onClick={saveChanges}
                className="bg-[#FF4940] text-white hover:bg-[#E63E36]"
              >
                <Save className="mr-2 h-4 w-4" />
                Guardar Cambios
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Schedule Grid */}
      <Card id="schedule-grid">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Horario Semanal
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {schedule.map((daySchedule) => (
              <div
                key={daySchedule.day}
                className={cn(
                  "flex items-center gap-4 rounded-lg border border-border p-4 transition-all",
                  highlightedDay === daySchedule.day && "ring-2 ring-[#FF4940] ring-offset-2",
                  !daySchedule.isOpen && "bg-muted/50"
                )}
              >
                <div className="w-28">
                  <p className="font-medium text-foreground">{daySchedule.day}</p>
                </div>
                
                <Switch
                  checked={daySchedule.isOpen}
                  onCheckedChange={() => toggleDay(daySchedule.day)}
                />
                
                <span
                  className={cn(
                    "w-20 text-sm",
                    daySchedule.isOpen ? "text-green-600" : "text-muted-foreground"
                  )}
                >
                  {daySchedule.isOpen ? "Abierto" : "Cerrado"}
                </span>

                {daySchedule.isOpen && (
                  <div className="flex items-center gap-2">
                    <Input
                      type="time"
                      value={daySchedule.openTime}
                      onChange={(e) => updateTime(daySchedule.day, "openTime", e.target.value)}
                      className="w-32"
                    />
                    <span className="text-muted-foreground">a</span>
                    <Input
                      type="time"
                      value={daySchedule.closeTime}
                      onChange={(e) => updateTime(daySchedule.day, "closeTime", e.target.value)}
                      className="w-32"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Acciones Rápidas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setSchedule((prev) =>
                  prev.map((s) => ({ ...s, isOpen: true }))
                )
                setHasChanges(true)
              }}
            >
              Abrir todos los días
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setSchedule((prev) =>
                  prev.map((s) => ({
                    ...s,
                    isOpen: !["Sábado", "Domingo"].includes(s.day),
                  }))
                )
                setHasChanges(true)
              }}
            >
              Solo días laborales
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setSchedule((prev) =>
                  prev.map((s) => ({
                    ...s,
                    openTime: "10:00",
                    closeTime: "22:00",
                  }))
                )
                setHasChanges(true)
              }}
            >
              Horario estándar (10am - 10pm)
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="border-[#FF4940]/20 bg-[#FFF5F5]">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Clock className="h-5 w-5 text-[#FF4940]" />
            <div>
              <p className="font-medium text-foreground">Nota importante</p>
              <p className="text-sm text-muted-foreground">
                Los cambios en el horario se reflejarán en la app de Rappi en un plazo de 15 minutos.
                Para pausas de emergencia, contacta a soporte.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
