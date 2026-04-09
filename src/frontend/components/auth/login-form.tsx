"use client"

import { useState } from "react"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FieldGroup, Field, FieldLabel } from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"
import { Eye, EyeOff, AlertCircle } from "lucide-react"

interface LoginFormProps {
  onForgotPassword: () => void
  onRegister: () => void
}

export function LoginForm({ onForgotPassword, onRegister }: LoginFormProps) {
  const { login, isLoading } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!email || !password) {
      setError("Por favor completa todos los campos")
      return
    }

    const success = await login(email, password)
    if (!success) {
      setError("Credenciales inválidas. Intenta con admin@latoscana.com / demo123")
    }
  }

  return (
    <Card className="w-full max-w-md border-0 shadow-2xl">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[#FF4940]">
          <span className="text-2xl font-bold text-white">R</span>
        </div>
        <CardTitle className="text-2xl font-bold text-foreground">Portal Partners</CardTitle>
        <CardDescription className="text-muted-foreground">
          Inicia sesión para gestionar tu negocio
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

          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="email">Correo electronico</FieldLabel>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="tu@correo.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                className="h-11"
                data-field="email"
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="password">Contrasena</FieldLabel>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="********"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  className="h-11 pr-10"
                  data-field="password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </Field>
          </FieldGroup>

          <div className="flex justify-end">
            <button
              type="button"
              onClick={onForgotPassword}
              className="text-sm text-[#FF4940] hover:underline"
              data-action="forgot-password"
            >
              Olvidaste tu contrasena?
            </button>
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            className="h-11 w-full bg-[#FF4940] text-white hover:bg-[#E63E36]"
            data-action="login"
          >
            {isLoading ? <Spinner className="h-4 w-4" /> : "Iniciar Sesion"}
          </Button>

          <div className="text-center text-sm text-muted-foreground">
            No tienes cuenta?{" "}
            <button
              type="button"
              onClick={onRegister}
              className="font-medium text-[#FF4940] hover:underline"
              data-action="register"
            >
              Registrate aqui
            </button>
          </div>
        </form>

        <div className="mt-6 rounded-lg bg-muted p-3 text-xs text-muted-foreground">
          <p className="font-medium">Credenciales de prueba:</p>
          <p>Email: admin@latoscana.com</p>
          <p>Contraseña: demo123</p>
        </div>
      </CardContent>
    </Card>
  )
}
