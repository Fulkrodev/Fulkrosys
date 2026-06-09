"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { ApiError } from "@/lib/api";
import {
  brandingSchema,
  type BrandingSettings,
  type AdminSettingsResponse,
} from "@/lib/admin-settings/schemas";
import { uploadBrandingLogo } from "@/lib/admin-settings/api";

type Props = {
  branding: BrandingSettings;
  onUpdate: (payload: BrandingSettings) => Promise<AdminSettingsResponse>;
  onLogoUploaded: (response: AdminSettingsResponse) => void;
};

export function BrandingTab({ branding, onUpdate, onLogoUploaded }: Props) {
  const [uploading, setUploading] = useState(false);

  const form = useForm<BrandingSettings>({
    resolver: zodResolver(brandingSchema),
    defaultValues: {
      logo_url: branding.logo_url ?? null,
      primary_color: branding.primary_color ?? "#7c3aed",
      secondary_color: branding.secondary_color ?? "#0c0a09",
      footer_text: branding.footer_text ?? "",
    },
  });

  const onSubmit = async (data: BrandingSettings) => {
    try {
      await onUpdate(data);
      toast.success("Branding actualizado");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al guardar branding",
      );
    }
  };

  const handleLogoFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const ALLOWED = ["image/png", "image/jpeg"];
    const MAX_SIZE = 2 * 1024 * 1024;

    if (!ALLOWED.includes(file.type)) {
      toast.error("Solo PNG o JPG permitidos");
      return;
    }
    if (file.size > MAX_SIZE) {
      toast.error("Logo excede 2MB");
      return;
    }

    setUploading(true);
    try {
      const result = await uploadBrandingLogo(file);
      onLogoUploaded(result);
      form.setValue("logo_url", result.branding.logo_url ?? null);
      toast.success("Logo subido");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al subir logo",
      );
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const currentLogoUrl = form.watch("logo_url");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Branding</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex flex-col gap-2">
            <Label>Logo corporativo</Label>
            {currentLogoUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={currentLogoUrl}
                alt="Logo actual"
                className="h-20 max-w-xs rounded border border-fulkro-ink-300/40 object-contain bg-fulkro-ink-50/30 p-2"
              />
            )}
            <Input
              type="file"
              accept="image/png,image/jpeg"
              onChange={handleLogoFile}
              disabled={uploading}
            />
            <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
              PNG o JPG · máximo 2MB
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="primary_color">Color primario</Label>
            <div className="flex items-center gap-3">
              <Input
                id="primary_color_picker"
                type="color"
                value={form.watch("primary_color") ?? "#7c3aed"}
                onChange={(e) =>
                  form.setValue("primary_color", e.target.value, {
                    shouldValidate: true,
                  })
                }
                className="h-10 w-16 cursor-pointer p-1"
              />
              <Input
                id="primary_color"
                {...form.register("primary_color")}
                placeholder="#7c3aed"
                className="font-mono text-sm"
              />
            </div>
            {form.formState.errors.primary_color && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.primary_color.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="secondary_color">Color secundario</Label>
            <div className="flex items-center gap-3">
              <Input
                id="secondary_color_picker"
                type="color"
                value={form.watch("secondary_color") ?? "#0c0a09"}
                onChange={(e) =>
                  form.setValue("secondary_color", e.target.value, {
                    shouldValidate: true,
                  })
                }
                className="h-10 w-16 cursor-pointer p-1"
              />
              <Input
                id="secondary_color"
                {...form.register("secondary_color")}
                placeholder="#0c0a09"
                className="font-mono text-sm"
              />
            </div>
            {form.formState.errors.secondary_color && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.secondary_color.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="footer_text">Texto pie de página</Label>
            <Input
              id="footer_text"
              {...form.register("footer_text")}
              placeholder="© 2026 FULKRO · Plataforma ENS"
              maxLength={500}
            />
            {form.formState.errors.footer_text && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.footer_text.message}
              </p>
            )}
          </div>

          <Button
            type="submit"
            disabled={form.formState.isSubmitting || uploading}
            className="self-start"
          >
            {form.formState.isSubmitting ? "Guardando..." : "Guardar branding"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
