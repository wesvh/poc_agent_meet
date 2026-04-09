"use client"

import { useState } from "react"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldLabel } from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"
import { AlertCircle, ArrowLeft, CheckCircle, Mail } from "lucide-react"

interface ForgotPasswordFormProps {
  onBack: () => void
}

export function ForgotPasswordForm({ onBack }: ForgotPasswordFormProps) {
  const { requestPasswordReset, isLoading } = useAuth()
  const [email, setEmail] = useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!email) {
      setError("Por favor ingresa tu correo electrónico")
      return
    }

    const result = await requestPasswordReset(email)
    if (result) {
      setSuccess(true)
    } else {
      setError("Error al enviar el correo. Verifica que sea un email válido.")
    }
  }

  if (success) {
    return (
      <Card className="w-full max-w-md border-0 shadow-2xl">
        <CardContent className="pt-8 pb-8">
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h2 className="mb-2 text-xl font-bold text-foreground">Revisa tu correo</h2>
            <p className="mb-6 text-sm text-muted-foreground">
              Hemos enviado un enlace de recuperación a <strong>{email}</strong>. 
              Revisa tu bandeja de entrada y sigue las instrucciones.
            </p>
            <div className="space-y-3">
              <Button
                onClick={onBack}
                className="w-full bg-[#FF4940] text-white hover:bg-[#E63E36]"
              >
                Volver al inicio de sesión
              </Button>
              <button
                onClick={() => setSuccess(false)}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                ¿No recibiste el correo? Intentar de nuevo
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md border-0 shadow-2xl">
      <CardHeader className="pb-2">
        <button
          id="forgot-back-btn"
          onClick={onBack}
          className="mb-2 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver al inicio
        </button>
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#FFF5F5]">
          <Mail className="h-7 w-7 text-[#FF4940]" />
        </div>
        <CardTitle className="text-center text-2xl font-bold text-foreground">
          Recuperar contraseña
        </CardTitle>
        <CardDescription className="text-center text-muted-foreground">
          Ingresa tu correo y te enviaremos instrucciones para restablecer tu contraseña
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Field>
            <FieldLabel htmlFor="email">Correo electrónico</FieldLabel>
            <Input
              id="email"
              type="email"
              placeholder="tu@correo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              className="h-11"
            />
          </Field>

          <Button
            id="forgot-submit-btn"
            type="submit"
            disabled={isLoading}
            className="h-11 w-full bg-[#FF4940] text-white hover:bg-[#E63E36]"
          >
            {isLoading ? <Spinner className="h-4 w-4" /> : "Enviar instrucciones"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
