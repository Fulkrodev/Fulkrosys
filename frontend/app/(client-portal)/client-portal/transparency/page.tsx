"use client";

/**
 * /client-portal/transparency · sub-atom 1.E.1.B.2.
 *
 * AI Act art.50 transparency log page · cliente-facing.
 *
 * R29 firmísimo · NO presión · friendly explainer · footer-linked
 * (NO sidebar pollution · sidebar permanece "indispensable-only"
 * per directive Marcos sub-atom 1.D.F.bis.III).
 */
import { TransparencyLogCard } from "@/components/client-portal/TransparencyLogCard";
import { PageContainer } from "@/components/layout/PageContainer";

export default function ClientTransparencyPage() {
  return (
    <PageContainer variant="reading">
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-slate-900">
            Transparencia IA
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Por transparencia europea (AI Act art.50) te mostramos cuándo se
            ha utilizado inteligencia artificial para ayudar a generar
            documentos o realizar análisis en tu proyecto. Marcos siempre
            revisa el resultado antes de entregártelo.
          </p>
        </header>

        <TransparencyLogCard days={180} />
      </div>
    </PageContainer>
  );
}
