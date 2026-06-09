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
import { Alert, AlertDescription } from "@/components/ui/alert";

import { ApiError } from "@/lib/api";
import {
  smtpSchema,
  type SmtpSettings,
  type AdminSettingsResponse,
} from "@/lib/admin-settings/schemas";
import { testSmtpConfig } from "@/lib/admin-settings/api";

type Props = {
  smtp: SmtpSettings;
  onUpdate: (payload: SmtpSettings) => Promise<AdminSettingsResponse>;
};

export function SmtpTab({ smtp, onUpdate }: Props) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);

  const form = useForm<SmtpSettings>({
    resolver: zodResolver(smtpSchema),
    defaultValues: {
      host: smtp.host ?? null,
      port: smtp.port ?? 587,
      username: smtp.username ?? null,
      password: smtp.password ?? null,
    },
  });

  const onSubmit = async (data: SmtpSettings) => {
    try {
      await onUpdate(data);
      toast.success("SMTP actualizado");
      setTestResult(null);
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al guardar SMTP",
      );
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testSmtpConfig({ use_admin_settings: true });
      setTestResult({
        ok: result.ok,
        message: result.ok
          ? `Email enviado a ${result.sent_to} via ${result.backend_used}`
          : `Error: ${result.error ?? "desconocido"}`,
      });
      if (result.ok) {
        toast.success("Test SMTP enviado");
      } else {
        toast.error("Test SMTP falló");
      }
    } catch (err) {
      const errMsg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al ejecutar test";
      setTestResult({ ok: false, message: errMsg });
      toast.error("Error test SMTP");
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>SMTP</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            Configuración SMTP custom. Si vacío, se usan valores de Settings
            env.
          </p>

          <div className="flex flex-col gap-2">
            <Label htmlFor="smtp_host">Host SMTP</Label>
            <Input
              id="smtp_host"
              {...form.register("host")}
              placeholder="smtp.example.com"
            />
            {form.formState.errors.host && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.host.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="smtp_port">Puerto</Label>
            <Input
              id="smtp_port"
              type="number"
              min={1}
              max={65535}
              {...form.register("port", { valueAsNumber: true })}
              placeholder="587"
            />
            {form.formState.errors.port && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.port.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="smtp_username">Usuario</Label>
            <Input
              id="smtp_username"
              {...form.register("username")}
              placeholder="user@example.com"
            />
            {form.formState.errors.username && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.username.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="smtp_password">Contraseña</Label>
            <Input
              id="smtp_password"
              type="password"
              {...form.register("password")}
              placeholder="••••••••"
            />
            {form.formState.errors.password && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.password.message}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={form.formState.isSubmitting}>
              {form.formState.isSubmitting ? "Guardando..." : "Guardar SMTP"}
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={handleTest}
              disabled={testing}
            >
              {testing ? "Enviando test..." : "Test envío"}
            </Button>
          </div>

          {testResult && (
            <Alert variant={testResult.ok ? "success" : "danger"}>
              <AlertDescription>{testResult.message}</AlertDescription>
            </Alert>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
