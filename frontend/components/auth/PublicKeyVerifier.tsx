/**
 * PublicKeyVerifier · sección verificación pública clave Ed25519 FULKRO.
 *
 * Consume GET /api/v1/auth/public-key (whitelist · sin auth requerida)
 * vía React Query. Permite copiar PEM al portapapeles y descargar como
 * .pem file. Renderiza key_id + algorithm para verificación trazable.
 *
 * SAN-B.MB-7.5 · cierre TODO-AUTH-KEY-ENDPOINT-001 (UI cliente).
 * Reutilizable en /client-portal/firma + futuras integraciones admin
 * settings.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { Copy, Download, ExternalLink, KeyRound, Loader2 } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { fulkroToast } from "@/lib/toast";

interface PublicKeyResponse {
  algorithm: string;
  format: string;
  public_key: string;
  key_id: string;
}

export function PublicKeyVerifier() {
  const { data, isLoading, isError } = useQuery<PublicKeyResponse>({
    queryKey: ["auth-public-key"],
    queryFn: async () => {
      const res = await fetch("/api/v1/auth/public-key", {
        credentials: "omit",
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      return res.json();
    },
    staleTime: 60 * 60 * 1000, // 1h · key cambia raramente
  });

  const handleCopy = React.useCallback(() => {
    if (!data) return;
    void navigator.clipboard.writeText(data.public_key);
    fulkroToast.success("Clave PEM copiada al portapapeles");
  }, [data]);

  const handleDownload = React.useCallback(() => {
    if (!data) return;
    const blob = new Blob([data.public_key], { type: "application/x-pem-file" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fulkro-public-key-${data.key_id}.pem`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    fulkroToast.success("Clave PEM descargada");
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> Cargando clave pública…
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-fulkro-ink-500">
          No se pudo cargar la clave pública. Inténtalo de nuevo más tarde.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound size={18} /> Verificación pública de firmas FULKRO
        </CardTitle>
        <CardDescription>
          Esta clave permite a cualquier auditor verificar las firmas Ed25519
          que FULKRO aplica a documentos firmados, archivos M07 (evidence),
          dossiers M25 y backups M26 — sin acceso al sistema.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <pre className="overflow-x-auto rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-100/40 p-3 text-xs leading-relaxed">
          {data.public_key}
        </pre>
        <div className="flex flex-wrap gap-2">
          <Button onClick={handleCopy} variant="outline" size="sm">
            <Copy size={14} className="mr-1" />
            Copiar PEM
          </Button>
          <Button onClick={handleDownload} size="sm">
            <Download size={14} className="mr-1" />
            Descargar (.pem)
          </Button>
          <a
            href="/docs/verify-signature"
            target="_blank"
            rel="noopener"
            className="inline-flex items-center gap-1 px-2 py-1.5 text-sm text-fulkro-primary-700 underline-offset-2 hover:underline"
          >
            <ExternalLink size={14} />
            Cómo verificar una firma
          </a>
        </div>
        <p className="text-xs text-fulkro-ink-500">
          Algoritmo: <span className="font-mono">{data.algorithm}</span> · Key
          ID: <span className="font-mono">{data.key_id}</span> · Formato:{" "}
          <span className="font-mono">{data.format}</span>
        </p>
      </CardContent>
    </Card>
  );
}
