"""Facturae 3.2.x XML generator · SAN-C MB-11.3.

Spec oficial: Orden HAP/1074/2014 · BOE 26/06/2014 (XSD Facturae 3.2.x).
Namespaces:
- fe: http://www.facturae.es/Facturae/2014/v3.2/Facturae
- ds: http://www.w3.org/2000/09/xmldsig#

Generador produce XML estructura mínima compliant: FileHeader + Parties
(Seller + Buyer) + Invoices (1 invoice). Suficiente para validación
schema XSD pre-firma XAdES (m15_billing/xades_signer.py).

Decisión técnica: NO incluimos Signature element aquí (lo añade
xades_signer si hay cert FNMT disponible). Eso permite generar XML
funcional pre-cliente sin requerir certificado.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lxml import etree


_NS_FACTURAE = "http://www.facturae.es/Facturae/2014/v3.2/Facturae"
_NS_DSIG = "http://www.w3.org/2000/09/xmldsig#"
_NSMAP = {"fe": _NS_FACTURAE, "ds": _NS_DSIG}


@dataclass(frozen=True)
class PartyData:
    """Datos parte (Seller emitter o Buyer AAPP)."""

    nombre_razon_social: str
    cif_nif: str
    address: str = ""
    postal_code: str = ""
    town: str = "Madrid"
    province: str = "Madrid"
    country_code: str = "ESP"
    # PersonTypeCode Facturae: 'F' persona física (autónomo) · 'J' jurídica.
    # Default 'J' (buyer AAPP). El seller emisor lo fija desde la identidad
    # fiscal (FUENTE ÚNICA · punto #44): autónomo → 'F'.
    person_type_code: str = "J"


@dataclass(frozen=True)
class InvoiceData:
    """Datos invoice mínimos para XML 3.2.x."""

    invoice_number: str
    issue_date: date
    amount_eur: Decimal
    description: str
    # AAPP DIR3 codes (mandatory per Orden 492/2014)
    dir3_oficina_contable: str
    dir3_organo_gestor: str
    dir3_unidad_tramitadora: str
    # IVA tipo (default 21% IVA general España)
    tax_rate_pct: Decimal = Decimal("21.00")


def generate_facturae_xml(
    *,
    seller: PartyData,
    buyer: PartyData,
    invoice: InvoiceData,
) -> bytes:
    """Genera XML Facturae 3.2.x compliant (sin firma XAdES).

    Returns:
        bytes con XML pretty-printed UTF-8 + declaration.
    """
    root = etree.Element(
        f"{{{_NS_FACTURAE}}}Facturae",
        nsmap=_NSMAP,
    )

    # FileHeader
    file_header = etree.SubElement(root, "FileHeader")
    etree.SubElement(file_header, "SchemaVersion").text = "3.2.2"
    etree.SubElement(file_header, "Modality").text = "I"  # Individual
    etree.SubElement(file_header, "InvoiceIssuerType").text = "EM"  # Emitter

    batch = etree.SubElement(file_header, "Batch")
    etree.SubElement(batch, "BatchIdentifier").text = invoice.invoice_number
    etree.SubElement(batch, "InvoicesCount").text = "1"

    total_invoices = etree.SubElement(batch, "TotalInvoicesAmount")
    etree.SubElement(total_invoices, "TotalAmount").text = (
        f"{invoice.amount_eur:.2f}"
    )

    total_outstanding = etree.SubElement(batch, "TotalOutstandingAmount")
    etree.SubElement(total_outstanding, "TotalAmount").text = (
        f"{invoice.amount_eur:.2f}"
    )

    total_executable = etree.SubElement(batch, "TotalExecutableAmount")
    etree.SubElement(total_executable, "TotalAmount").text = (
        f"{invoice.amount_eur:.2f}"
    )

    etree.SubElement(batch, "InvoiceCurrencyCode").text = "EUR"

    # Parties (Seller + Buyer)
    parties = etree.SubElement(root, "Parties")
    _build_party(parties, "SellerParty", seller)
    _build_party(parties, "BuyerParty", buyer, dir3=invoice)

    # Invoices (single invoice in this batch)
    invoices = etree.SubElement(root, "Invoices")
    inv = etree.SubElement(invoices, "Invoice")

    inv_header = etree.SubElement(inv, "InvoiceHeader")
    etree.SubElement(inv_header, "InvoiceNumber").text = invoice.invoice_number
    etree.SubElement(inv_header, "InvoiceDocumentType").text = "FC"  # Factura completa
    etree.SubElement(inv_header, "InvoiceClass").text = "OO"  # Original

    issue_data = etree.SubElement(inv, "InvoiceIssueData")
    etree.SubElement(issue_data, "IssueDate").text = invoice.issue_date.isoformat()
    etree.SubElement(issue_data, "InvoiceCurrencyCode").text = "EUR"
    etree.SubElement(issue_data, "TaxCurrencyCode").text = "EUR"
    etree.SubElement(issue_data, "LanguageName").text = "es"

    # Taxes Outputs
    taxes = etree.SubElement(inv, "TaxesOutputs")
    tax = etree.SubElement(taxes, "Tax")
    etree.SubElement(tax, "TaxTypeCode").text = "01"  # IVA
    etree.SubElement(tax, "TaxRate").text = f"{invoice.tax_rate_pct:.2f}"
    taxable_base = etree.SubElement(tax, "TaxableBase")
    etree.SubElement(taxable_base, "TotalAmount").text = (
        f"{invoice.amount_eur:.2f}"
    )
    tax_amount = etree.SubElement(tax, "TaxAmount")
    etree.SubElement(tax_amount, "TotalAmount").text = (
        f"{(invoice.amount_eur * invoice.tax_rate_pct / Decimal('100')):.2f}"
    )

    # InvoiceTotals
    totals = etree.SubElement(inv, "InvoiceTotals")
    etree.SubElement(totals, "TotalGrossAmount").text = (
        f"{invoice.amount_eur:.2f}"
    )
    etree.SubElement(totals, "TotalGrossAmountBeforeTaxes").text = (
        f"{invoice.amount_eur:.2f}"
    )
    etree.SubElement(totals, "TotalTaxOutputs").text = (
        f"{(invoice.amount_eur * invoice.tax_rate_pct / Decimal('100')):.2f}"
    )
    etree.SubElement(totals, "TotalTaxesWithheld").text = "0.00"
    etree.SubElement(totals, "InvoiceTotal").text = (
        f"{(invoice.amount_eur * (Decimal('1') + invoice.tax_rate_pct / Decimal('100'))):.2f}"
    )
    etree.SubElement(totals, "TotalOutstandingAmount").text = (
        f"{(invoice.amount_eur * (Decimal('1') + invoice.tax_rate_pct / Decimal('100'))):.2f}"
    )
    etree.SubElement(totals, "TotalExecutableAmount").text = (
        f"{(invoice.amount_eur * (Decimal('1') + invoice.tax_rate_pct / Decimal('100'))):.2f}"
    )

    # Items
    items = etree.SubElement(inv, "Items")
    item_line = etree.SubElement(items, "InvoiceLine")
    etree.SubElement(item_line, "ItemDescription").text = invoice.description
    etree.SubElement(item_line, "Quantity").text = "1.000000"
    etree.SubElement(item_line, "UnitPriceWithoutTax").text = (
        f"{invoice.amount_eur:.6f}"
    )
    etree.SubElement(item_line, "TotalCost").text = f"{invoice.amount_eur:.2f}"
    etree.SubElement(item_line, "GrossAmount").text = f"{invoice.amount_eur:.2f}"

    return etree.tostring(
        root, pretty_print=True, encoding="UTF-8", xml_declaration=True,
    )


def _build_party(
    parent: "etree._Element",
    tag: str,
    data: PartyData,
    *,
    dir3: "InvoiceData | None" = None,
) -> None:
    party = etree.SubElement(parent, tag)
    tax_id = etree.SubElement(party, "TaxIdentification")
    etree.SubElement(tax_id, "PersonTypeCode").text = data.person_type_code
    etree.SubElement(tax_id, "ResidenceTypeCode").text = "R"  # Residente
    etree.SubElement(tax_id, "TaxIdentificationNumber").text = data.cif_nif

    # AAPP DIR3 codes (solo BuyerParty si AAPP)
    if dir3 is not None and tag == "BuyerParty":
        admin_centres = etree.SubElement(party, "AdministrativeCentres")
        for role, code in (
            ("01", dir3.dir3_oficina_contable),  # OC
            ("02", dir3.dir3_organo_gestor),     # OG
            ("03", dir3.dir3_unidad_tramitadora),  # UT
        ):
            ac = etree.SubElement(admin_centres, "AdministrativeCentre")
            etree.SubElement(ac, "CentreCode").text = code
            etree.SubElement(ac, "RoleTypeCode").text = role
            etree.SubElement(ac, "Name").text = data.nombre_razon_social

    legal = etree.SubElement(party, "LegalEntity")
    etree.SubElement(legal, "CorporateName").text = data.nombre_razon_social
    address = etree.SubElement(legal, "AddressInSpain")
    etree.SubElement(address, "Address").text = data.address or "—"
    etree.SubElement(address, "PostCode").text = data.postal_code or "00000"
    etree.SubElement(address, "Town").text = data.town
    etree.SubElement(address, "Province").text = data.province
    etree.SubElement(address, "CountryCode").text = data.country_code
