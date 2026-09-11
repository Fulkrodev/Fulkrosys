"use client";

/**
 * EntregablesGeneratorPanel · P2 · el cable que faltaba.
 *
 * El generador genérico del Motor 6 existe desde el primer día y funciona:
 * `POST /api/v1/projects/{id}/documents/generate` saca 63 de los 65
 * entregables del catálogo en una pasada. Y no lo llamaba NADIE —
 * `grep -rn "documents/generate" frontend/` devolvía cero resultados. El
 * checklist sabía perfectamente qué faltaba, pero sólo lo publicaba como cifra
 * ("1 de 28"), nunca como lista accionable. El motor estaba entero y le
 * faltaba el cable hasta la pantalla.
 *
 * Este panel lo pone: lee qué exige el checklist para la categoría del
 * proyecto, muestra qué falta, y los genera en tanda con su progreso y su
 * gestión de error — sin abortar la tanda cuando uno falla, porque un fallo en
 * el documento 12 no puede tirar los 11 que ya salieron.
 */
import * as React from "react";
import { AlertCircle, CheckCircle2, FileStack, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type EntregablesRequeridos,
  generateDocumentoPorCodigo,
  getEntregablesRequeridos,
} from "@/lib/api/documents";

interface Props {
  projectId: string;
}

interface Fallo {
  codigo: string;
  motivo: string;
}

export function EntregablesGeneratorPanel({ projectId }: Props) {
  const [datos, setDatos] = React.useState<EntregablesRequeridos | null>(null);
  const [cargando, setCargando] = React.useState(true);
  const [errorCarga, setErrorCarga] = React.useState<string | null>(null);

  const [enMarcha, setEnMarcha] = React.useState(false);
  const [hechos, setHechos] = React.useState(0);
  const [actual, setActual] = React.useState<string | null>(null);
  const [fallos, setFallos] = React.useState<Fallo[]>([]);
  const [bloqueo, setBloqueo] = React.useState<string | null>(null);

  const cargar = React.useCallback(async () => {
    setCargando(true);
    setErrorCarga(null);
    try {
      setDatos(await getEntregablesRequeridos(projectId));
    } catch (e) {
      setErrorCarga(e instanceof Error ? e.message : "No se pudo consultar.");
    } finally {
      setCargando(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    void cargar();
  }, [cargar]);

  const generarLosQueFaltan = async () => {
    if (!datos || datos.faltan.length === 0) return;
    setEnMarcha(true);
    setHechos(0);
    setFallos([]);
    const nuevosFallos: Fallo[] = [];

    // Un fallo suelto es del documento; tres seguidos con el MISMO motivo son
    // una puerta que afecta a todos (la más común: la DdA sin congelar, 409 ·
    // gate frozen_dda). Sólo en ese caso se para: parar al primer fallo sería
    // dejar que un documento con su propio problema tumbe los otros 26.
    let bloqueoSistemico: string | null = null;
    let seguidos = 0;
    let ultimoMotivo = "";

    for (let i = 0; i < datos.faltan.length; i += 1) {
      const codigo = datos.faltan[i];
      setActual(codigo);
      try {
        await generateDocumentoPorCodigo(projectId, codigo);
        seguidos = 0;
      } catch (e) {
        const motivo = e instanceof Error ? e.message : "error desconocido";
        nuevosFallos.push({ codigo, motivo });
        seguidos = motivo === ultimoMotivo ? seguidos + 1 : 1;
        ultimoMotivo = motivo;
        if (seguidos >= 3) {
          bloqueoSistemico = motivo;
          break;
        }
      }
      setHechos((n) => n + 1);
    }

    if (bloqueoSistemico) {
      setActual(null);
      setEnMarcha(false);
      setFallos([]);
      setBloqueo(bloqueoSistemico);
      toast.error("Se paró la tanda", { description: bloqueoSistemico });
      await cargar();
      return;
    }
    setBloqueo(null);

    setActual(null);
    setFallos(nuevosFallos);
    setEnMarcha(false);
    await cargar();

    const generados = datos.faltan.length - nuevosFallos.length;
    if (nuevosFallos.length === 0) {
      toast.success(`${generados} entregables generados`, {
        description: "Registrados en el expediente, con su huella y su firma.",
      });
    } else {
      toast.warning(`${generados} generados · ${nuevosFallos.length} fallaron`, {
        description: "Abajo tienes el motivo de cada uno.",
      });
    }
  };

  if (cargando) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Entregables del expediente</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (errorCarga || !datos) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Entregables del expediente</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="danger">
            <AlertCircle size={16} strokeWidth={2.2} />
            <AlertTitle>No se pudo consultar qué falta</AlertTitle>
            <AlertDescription>{errorCarga}</AlertDescription>
          </Alert>
          <Button
            className="mt-3"
            variant="outline"
            onClick={() => void cargar()}
            data-testid="entregables-retry"
          >
            Reintentar
          </Button>
        </CardContent>
      </Card>
    );
  }

  const completo = datos.faltan.length === 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileStack size={18} strokeWidth={2.2} />
          Entregables del expediente · {datos.categoria}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-[color:var(--fulkro-body)]">
          El expediente que recibe el auditor se arma con los documentos
          registrados del proyecto. Ahora mismo hay{" "}
          <strong data-testid="entregables-presentes">
            {datos.presentes_count} de {datos.total}
          </strong>{" "}
          de los que el checklist exige para la categoría {datos.categoria}.
        </p>

        {completo ? (
          <Alert>
            <CheckCircle2 size={16} strokeWidth={2.2} />
            <AlertTitle>No falta ninguno</AlertTitle>
            <AlertDescription>
              Los {datos.total} entregables exigidos están generados y
              registrados.
            </AlertDescription>
          </Alert>
        ) : (
          <>
            <div className="text-sm text-[color:var(--fulkro-body)]">
              Faltan <strong>{datos.faltan.length}</strong>:{" "}
              <span className="font-mono text-xs">
                {datos.faltan.join(" · ")}
              </span>
            </div>
            <Button
              onClick={() => void generarLosQueFaltan()}
              disabled={enMarcha}
              data-testid="generar-entregables"
            >
              {enMarcha ? (
                <>
                  <Loader2 size={16} strokeWidth={2.4} className="animate-spin" />
                  Generando {actual ?? "…"} · {hechos} de {datos.faltan.length}
                </>
              ) : (
                <>
                  <FileStack size={16} strokeWidth={2.4} />
                  Generar los {datos.faltan.length} que faltan
                </>
              )}
            </Button>
          </>
        )}

        {datos.faltan_sin_plantilla.length > 0 && (
          <Alert>
            <AlertCircle size={16} strokeWidth={2.2} />
            <AlertTitle>
              {datos.faltan_sin_plantilla.length} sin plantilla en el catálogo
            </AlertTitle>
            <AlertDescription>
              <span className="font-mono text-xs">
                {datos.faltan_sin_plantilla.join(" · ")}
              </span>
              . Estos no se pueden generar todavía: no tienen plantilla, así que
              el botón de arriba no los intenta.
            </AlertDescription>
          </Alert>
        )}

        {bloqueo && (
          <Alert variant="danger">
            <AlertCircle size={16} strokeWidth={2.2} />
            <AlertTitle>Se paró la tanda</AlertTitle>
            <AlertDescription>
              Tres entregables seguidos fallaron por lo mismo, así que no es
              problema de uno sino una condición que los afecta a todos:{" "}
              {bloqueo} Resuélvela y vuelve a intentarlo.
            </AlertDescription>
          </Alert>
        )}

        {fallos.length > 0 && (
          <Alert variant="danger">
            <AlertCircle size={16} strokeWidth={2.2} />
            <AlertTitle>{fallos.length} no se pudieron generar</AlertTitle>
            <AlertDescription>
              <ul className="mt-1 flex flex-col gap-1">
                {fallos.map((f) => (
                  <li key={f.codigo} className="text-xs">
                    <span className="font-mono font-semibold">{f.codigo}</span>
                    {" — "}
                    {f.motivo}
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
