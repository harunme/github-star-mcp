import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cn } from "@/lib/utils"

const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    asChild?: boolean
    variant?: "primary" | "secondary" | "ghost" | "outline" | "destructive" | "link"
    size?: "sm" | "md" | "lg" | "icon"
  }
>(({ className, variant = "primary", size = "md", asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button"
  const variants = {
    primary: [
      "bg-primary text-primary-foreground",
      "hover:brightness-110 active:brightness-90",
      "shadow-[0_1px_2px_rgba(0,0,0,0.2)]",
    ].join(" "),
    secondary: [
      "bg-secondary text-secondary-foreground",
      "hover:bg-secondary/80 active:bg-secondary/70",
    ].join(" "),
    ghost: [
      "text-primary",
      "hover:bg-secondary active:bg-secondary/70",
    ].join(" "),
    outline: [
      "border border-border bg-transparent text-foreground",
      "hover:bg-secondary active:bg-secondary/70",
    ].join(" "),
    destructive: [
      "bg-destructive text-destructive-foreground",
      "hover:brightness-110 active:brightness-90",
    ].join(" "),
    link: "text-primary underline-offset-4 hover:underline",
  }
  const sizes = {
    sm: "h-9 px-4 rounded-lg text-[15px]",
    md: "h-11 px-5 rounded-xl text-[17px]",
    lg: "h-12 px-6 rounded-xl text-[17px]",
    icon: "h-11 w-11 rounded-xl",
  }
  return (
    <Comp
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap font-normal",
        "transition-all duration-150 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:opacity-40",
        variants[variant],
        sizes[size],
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Button.displayName = "Button"

export { Button }
