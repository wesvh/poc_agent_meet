"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Field, FieldLabel } from "@/components/ui/field"
import { mockProducts, mockToppings, type Product, type Topping } from "@/lib/mock-data"
import { Package, Plus, Pencil, Search, X } from "lucide-react"
import { cn } from "@/lib/utils"

export function CatalogSection() {
  const [products, setProducts] = useState<Product[]>(mockProducts)
  const [toppings, setToppings] = useState<Topping[]>(mockToppings)
  const [searchTerm, setSearchTerm] = useState("")
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [editForm, setEditForm] = useState({ name: "", price: 0, stock: 0 })
  const [highlightedId, setHighlightedId] = useState<string | null>(null)

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      minimumFractionDigits: 0,
    }).format(value)
  }

  const filteredProducts = products.filter(
    (p) =>
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.category.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const toggleProductStatus = (productId: string) => {
    setProducts((prev) =>
      prev.map((p) => (p.id === productId ? { ...p, isActive: !p.isActive } : p))
    )
    highlightElement(productId)
  }

  const toggleToppingStatus = (toppingId: string) => {
    setToppings((prev) =>
      prev.map((t) => (t.id === toppingId ? { ...t, isActive: !t.isActive } : t))
    )
    highlightElement(toppingId)
  }

  const openEditModal = (product: Product) => {
    setEditingProduct(product)
    setEditForm({ name: product.name, price: product.price, stock: product.stock })
  }

  const saveProduct = () => {
    if (editingProduct) {
      setProducts((prev) =>
        prev.map((p) =>
          p.id === editingProduct.id
            ? { ...p, name: editForm.name, price: editForm.price, stock: editForm.stock }
            : p
        )
      )
      highlightElement(editingProduct.id)
      setEditingProduct(null)
    }
  }

  const highlightElement = (id: string) => {
    setHighlightedId(id)
    setTimeout(() => setHighlightedId(null), 2000)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Catálogo</h1>
          <p className="text-muted-foreground">Gestiona tus productos y complementos</p>
        </div>
        <Button className="bg-[#FF4940] text-white hover:bg-[#E63E36]">
          <Plus className="mr-2 h-4 w-4" />
          Agregar Producto
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Buscar productos..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Products List */}
      <Card id="products-list">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Productos ({filteredProducts.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {filteredProducts.map((product) => (
              <div
                key={product.id}
                id={`product-${product.id}`}
                className={cn(
                  "flex items-center justify-between rounded-lg border border-border p-4 transition-all",
                  highlightedId === product.id && "ring-2 ring-[#FF4940] ring-offset-2",
                  !product.isActive && "opacity-60"
                )}
              >
                <div className="flex items-center gap-4">
                  <div className="h-16 w-16 rounded-lg bg-muted" />
                  <div>
                    <p className="font-medium text-foreground">{product.name}</p>
                    <p className="text-sm text-muted-foreground">{product.description}</p>
                    <p className="text-xs text-muted-foreground">
                      {product.category} | Stock: {product.stock}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-lg font-semibold text-foreground">
                    {formatCurrency(product.price)}
                  </span>
                  <Switch
                    checked={product.isActive}
                    onCheckedChange={() => toggleProductStatus(product.id)}
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => openEditModal(product)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Toppings List */}
      <Card id="toppings-list">
        <CardHeader>
          <CardTitle>Toppings / Complementos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {toppings.map((topping) => (
              <div
                key={topping.id}
                id={`topping-${topping.id}`}
                className={cn(
                  "flex items-center justify-between rounded-lg border border-border p-3 transition-all",
                  highlightedId === topping.id && "ring-2 ring-[#FF4940] ring-offset-2",
                  !topping.isActive && "opacity-60"
                )}
              >
                <div>
                  <p className="font-medium text-foreground">{topping.name}</p>
                  <p className="text-sm text-muted-foreground">{formatCurrency(topping.price)}</p>
                </div>
                <Switch
                  checked={topping.isActive}
                  onCheckedChange={() => toggleToppingStatus(topping.id)}
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Edit Modal */}
      <Dialog open={!!editingProduct} onOpenChange={() => setEditingProduct(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Producto</DialogTitle>
            <DialogDescription>
              Modifica los detalles del producto
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <Field>
              <FieldLabel>Nombre</FieldLabel>
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm((prev) => ({ ...prev, name: e.target.value }))}
              />
            </Field>
            <Field>
              <FieldLabel>Precio (COP)</FieldLabel>
              <Input
                type="number"
                value={editForm.price}
                onChange={(e) => setEditForm((prev) => ({ ...prev, price: Number(e.target.value) }))}
              />
            </Field>
            <Field>
              <FieldLabel>Stock</FieldLabel>
              <Input
                type="number"
                value={editForm.stock}
                onChange={(e) => setEditForm((prev) => ({ ...prev, stock: Number(e.target.value) }))}
              />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingProduct(null)}>
              Cancelar
            </Button>
            <Button onClick={saveProduct} className="bg-[#FF4940] text-white hover:bg-[#E63E36]">
              Guardar Cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
