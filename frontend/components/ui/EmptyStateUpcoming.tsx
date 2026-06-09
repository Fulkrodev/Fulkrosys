import { Construction } from "lucide-react";

interface EmptyStateUpcomingProps {
  title: string;
  description: string;
}

export function EmptyStateUpcoming({
  title,
  description,
}: EmptyStateUpcomingProps) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-24 text-center">
      <div className="rounded-full bg-fulkro-primary-50 p-4">
        <Construction className="h-8 w-8 text-fulkro-primary-500" />
      </div>
      <h3 className="mt-6 text-lg font-semibold text-fulkro-ink-900">
        {title}
      </h3>
      <p className="mt-2 max-w-md text-sm text-fulkro-ink-700">{description}</p>
      <p className="mt-4 text-xs text-fulkro-ink-500">
        Disponible próximamente.
      </p>
    </div>
  );
}
