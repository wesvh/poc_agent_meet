"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { mockFAQ } from "@/lib/mock-data"
import {
  HelpCircle,
  MessageCircle,
  Search,
  Phone,
  Mail,
  FileText,
  ExternalLink,
} from "lucide-react"

export function SupportSection() {
  const [searchTerm, setSearchTerm] = useState("")
  const [chatOpen, setChatOpen] = useState(false)

  const filteredFAQ = mockFAQ.filter(
    (item) =>
      item.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.answer.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Soporte</h1>
          <p className="text-muted-foreground">Centro de ayuda y asistencia</p>
        </div>
        <Button
          id="chat-btn"
          onClick={() => setChatOpen(true)}
          className="bg-[#FF4940] text-white hover:bg-[#E63E36]"
        >
          <MessageCircle className="mr-2 h-4 w-4" />
          Chat con Soporte
        </Button>
      </div>

      {/* Contact Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FFF5F5]">
              <Phone className="h-5 w-5 text-[#FF4940]" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Línea directa</p>
              <p className="font-medium text-foreground">01 800 RAPPI</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FFF5F5]">
              <Mail className="h-5 w-5 text-[#FF4940]" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Email</p>
              <p className="font-medium text-foreground">partners@rappi.com</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FFF5F5]">
              <MessageCircle className="h-5 w-5 text-[#FF4940]" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Chat</p>
              <p className="font-medium text-foreground">24/7 disponible</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* FAQ Section */}
      <Card id="faq-section">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HelpCircle className="h-5 w-5" />
            Preguntas Frecuentes
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Search */}
          <div className="relative mb-6">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Buscar en preguntas frecuentes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* FAQ Accordion */}
          <Accordion type="single" collapsible className="w-full">
            {filteredFAQ.map((item, index) => (
              <AccordionItem key={index} value={`item-${index}`}>
                <AccordionTrigger className="text-left">
                  {item.question}
                </AccordionTrigger>
                <AccordionContent className="text-muted-foreground">
                  {item.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>

          {filteredFAQ.length === 0 && (
            <p className="py-8 text-center text-muted-foreground">
              No se encontraron resultados para tu búsqueda
            </p>
          )}
        </CardContent>
      </Card>

      {/* Resources */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Recursos Útiles
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            <a
              href="#"
              className="flex items-center justify-between rounded-lg border border-border p-4 transition-all hover:bg-muted/50"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium text-foreground">Guía de inicio</span>
              </div>
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
            </a>
            <a
              href="#"
              className="flex items-center justify-between rounded-lg border border-border p-4 transition-all hover:bg-muted/50"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium text-foreground">Políticas de calidad</span>
              </div>
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
            </a>
            <a
              href="#"
              className="flex items-center justify-between rounded-lg border border-border p-4 transition-all hover:bg-muted/50"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium text-foreground">Términos del servicio</span>
              </div>
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
            </a>
            <a
              href="#"
              className="flex items-center justify-between rounded-lg border border-border p-4 transition-all hover:bg-muted/50"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium text-foreground">Video tutoriales</span>
              </div>
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
            </a>
          </div>
        </CardContent>
      </Card>

      {/* Chat Modal Simulation */}
      {chatOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-md">
            <CardHeader className="border-b border-border">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <MessageCircle className="h-5 w-5 text-[#FF4940]" />
                  Chat con Soporte
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setChatOpen(false)}>
                  &times;
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-4">
              <div className="mb-4 h-64 rounded-lg bg-muted p-4">
                <div className="mb-3 rounded-lg bg-[#FF4940] p-3 text-white">
                  <p className="text-sm">
                    ¡Hola! Soy tu asistente virtual de Rappi Partners. ¿En qué puedo ayudarte hoy?
                  </p>
                </div>
                <p className="text-center text-sm text-muted-foreground">
                  Esta es una simulación del chat de soporte
                </p>
              </div>
              <div className="flex gap-2">
                <Input placeholder="Escribe tu mensaje..." className="flex-1" />
                <Button className="bg-[#FF4940] text-white hover:bg-[#E63E36]">
                  Enviar
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
