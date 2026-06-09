import Image from "next/image";

interface LogoProps {
  variant?: "light" | "dark" | "mono-white" | "black" | "icon";
  size?: "sm" | "md" | "lg";
  className?: string;
  priority?: boolean;
}

const dimensions = {
  sm: { width: 100, height: 32 },
  md: { width: 140, height: 44 },
  lg: { width: 200, height: 64 },
};

const fileMap: Record<NonNullable<LogoProps["variant"]>, string> = {
  light: "fulkro-logo-light",
  dark: "fulkro-logo-dark",
  "mono-white": "fulkro-logo-mono-white",
  black: "fulkro-logo-black",
  icon: "fulkro-icon-512",
};

export function Logo({
  variant = "light",
  size = "md",
  className = "",
  priority = false,
}: LogoProps) {
  const { width, height } = dimensions[size];
  return (
    <Image
      src={`/brand/${fileMap[variant]}.svg`}
      alt="FULKRO — El punto de apoyo del consultor ENS"
      width={width}
      height={height}
      className={className}
      priority={priority}
    />
  );
}
