import Image from "next/image";

interface LogoProps {
  size?: "sm" | "md" | "lg";
}

export function Logo({ size = "md" }: LogoProps) {
  const heights = { sm: 36, md: 44, lg: 80 };
  const widths = { sm: 120, md: 148, lg: 260 };
  const h = heights[size];
  const w = widths[size];

  return (
    <Image
      src="/logo_maj.png"
      alt="Presto"
      width={w}
      height={h}
      priority
      className="mix-blend-multiply dark:mix-blend-screen object-contain"
    />
  );
}
