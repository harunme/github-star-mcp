import * as React from "react"
import { cn } from "@/lib/utils"

const Badge = React.forwardRef<
  HTMLSpanElement,
  React.HTMLAttributes<HTMLSpanElement> & {
    variant?: "default" | "secondary" | "destructive" | "outline"
  }
>(({ className, variant = "default", ...props }, ref) => {
  const variants = {
    default: "bg-primary/15 text-primary-foreground",
    secondary: "bg-secondary text-secondary-foreground",
    destructive: "bg-destructive/15 text-destructive",
    outline: "bg-transparent text-muted-foreground border border-border",
  }
  return (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-lg px-2.5 py-0.5 text-[12px] font-medium tracking-wide transition-colors",
        variants[variant],
        className
      )}
      {...props}
    />
  )
})
Badge.displayName = "Badge"

export { Badge }
