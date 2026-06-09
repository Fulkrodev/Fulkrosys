"""Pricing catalog (Apéndice M spec v2.1) — modelos económicos deterministas.

5 modelos precargados para calcular propuestas en segundos.
Importes calculados vía fórmula determinista. El LLM nunca inventa precios.
"""
from __future__ import annotations

from typing import Any


PRICING_CATALOG: list[dict[str, Any]] = [
    {
        "id": "basica_fijo",
        "nombre": "Básica — Precio fijo",
        "descripcion": "Ideal para clientes ENS categoría BÁSICA sin alcance complejo.",
        "aplicable_categoria": ["BASICA"],
        "formula": {
            "base": 6500,
            "por_empleado_extra_de_10": 80,
            "por_sistema_extra_de_2": 600,
        },
        "rango_min": 6500,
        "rango_max": 14000,
        "hitos_pago": [
            {"nombre": "anticipo", "pct": 30},
            {"nombre": "mitad_proyecto", "pct": 40},
            {"nombre": "cierre", "pct": 30},
        ],
    },
    {
        "id": "media_hitos",
        "nombre": "Media — Por hitos",
        "descripcion": "Para ENS categoría MEDIA. Pago por hitos entregables.",
        "aplicable_categoria": ["MEDIA"],
        "formula": {
            "base": 22000,
            "por_empleado_extra_de_25": 150,
            "por_sistema_extra_de_3": 1200,
            "por_ubicacion_extra": 1800,
            "por_sector_regulado_extra": 3000,
        },
        "rango_min": 22000,
        "rango_max": 55000,
        "hitos_pago": [
            {"nombre": "firma", "pct": 20},
            {"nombre": "diagnostico", "pct": 15},
            {"nombre": "diseno_sgsi", "pct": 20},
            {"nombre": "implantacion_70", "pct": 25},
            {"nombre": "dossier", "pct": 15},
            {"nombre": "certificacion", "pct": 5},
        ],
    },
    {
        "id": "alta_fases_exito",
        "nombre": "Alta — Fases + bonus éxito",
        "descripcion": "Para ENS categoría ALTA. Incluye bonus por certificación exitosa.",
        "aplicable_categoria": ["ALTA"],
        "formula": {
            "base": 48000,
            "por_empleado_extra_de_50": 180,
            "por_sistema_extra_de_5": 2000,
            "por_ubicacion_extra": 2500,
            "por_cpd_extra": 4500,
            "bonus_exito": 8000,
        },
        "rango_min": 48000,
        "rango_max": 140000,
        "hitos_pago": [
            {"nombre": "firma", "pct": 15},
            {"nombre": "diagnostico", "pct": 10},
            {"nombre": "diseno_sgsi", "pct": 15},
            {"nombre": "implantacion_50", "pct": 15},
            {"nombre": "implantacion_90", "pct": 15},
            {"nombre": "dossier", "pct": 15},
            {"nombre": "certificacion", "pct": 10},
            {"nombre": "bonus_exito", "pct": 5},
        ],
    },
    {
        "id": "retainer_basico",
        "nombre": "Retainer Básico post-certificación",
        "descripcion": "Mantenimiento mensual post-certificación.",
        "aplicable_categoria": ["BASICA", "MEDIA"],
        "formula": {"mensual": 450, "por_sistema_extra": 50},
        "rango_min": 450,
        "rango_max": 900,
        "hitos_pago": [{"nombre": "mensual", "pct": 100}],
    },
    {
        "id": "retainer_premium",
        "nombre": "Retainer Premium",
        "descripcion": "Mantenimiento + pentest continuo.",
        "aplicable_categoria": ["MEDIA", "ALTA"],
        "formula": {
            "mensual": 1200,
            "por_sistema_extra": 100,
            "pentest_continuo_extra": 300,
        },
        "rango_min": 1200,
        "rango_max": 3000,
        "hitos_pago": [{"nombre": "mensual", "pct": 100}],
    },
]


IVA_DEFAULT = 21.0


class PricingModelNotFoundError(ValueError):
    pass


class PricingService:
    """Calcula importes de propuestas desde modelos in-memory (Apéndice M)."""

    def __init__(self):
        self._by_id = {m["id"]: m for m in PRICING_CATALOG}

    def get_model(self, model_id: str) -> dict:
        if model_id not in self._by_id:
            raise PricingModelNotFoundError(f"Pricing model '{model_id}' no existe")
        return self._by_id[model_id]

    def get_models_for_categoria(self, categoria: str) -> list[dict]:
        cat = (categoria or "").upper()
        return [m for m in PRICING_CATALOG if cat in m["aplicable_categoria"]]

    def list_all(self) -> list[dict]:
        return list(PRICING_CATALOG)

    def calculate_price(
        self,
        model_id: str,
        empleados: int = 0,
        sistemas: int = 0,
        ubicaciones: int = 1,
        sector_regulado: bool = False,
        cpds: int = 0,
        meses_retainer: int = 1,
        pentest_continuo: bool = False,
        iva_percent: float = IVA_DEFAULT,
    ) -> dict:
        """Calcula importe total + desglose + hitos de pago + IVA.

        Determinista: mismos inputs producen mismos outputs.
        Retorna dict con: model_id, base, extras, total, hitos, iva, total_con_iva.
        """
        model = self.get_model(model_id)
        formula = model["formula"]
        extras: list[dict] = []

        # Retainers (formula "mensual")
        if "mensual" in formula:
            base = float(formula["mensual"])
            label_base = f"Retainer mensual (×{meses_retainer} meses)"
            extras.append({"concepto": label_base, "importe": base * meses_retainer - base})
            total_sin_iva = base * meses_retainer
            # Extra por sistema adicional
            if sistemas > 1 and "por_sistema_extra" in formula:
                add = (sistemas - 1) * float(formula["por_sistema_extra"]) * meses_retainer
                extras.append({
                    "concepto": f"{sistemas - 1} sistemas adicionales",
                    "importe": add,
                })
                total_sin_iva += add
            if pentest_continuo and "pentest_continuo_extra" in formula:
                add = float(formula["pentest_continuo_extra"]) * meses_retainer
                extras.append({"concepto": "Pentest continuo", "importe": add})
                total_sin_iva += add
        else:
            # Modelos proyecto (Basica / Media / Alta)
            base = float(formula["base"])
            total_sin_iva = base

            # Empleados extra
            for key, threshold in (
                ("por_empleado_extra_de_10", 10),
                ("por_empleado_extra_de_25", 25),
                ("por_empleado_extra_de_50", 50),
            ):
                if key in formula and empleados > threshold:
                    delta = empleados - threshold
                    add = delta * float(formula[key])
                    extras.append({
                        "concepto": f"{delta} empleados adicionales (>{threshold})",
                        "importe": add,
                    })
                    total_sin_iva += add

            # Sistemas extra
            for key, threshold in (
                ("por_sistema_extra_de_2", 2),
                ("por_sistema_extra_de_3", 3),
                ("por_sistema_extra_de_5", 5),
            ):
                if key in formula and sistemas > threshold:
                    delta = sistemas - threshold
                    add = delta * float(formula[key])
                    extras.append({
                        "concepto": f"{delta} sistemas adicionales (>{threshold})",
                        "importe": add,
                    })
                    total_sin_iva += add

            # Ubicaciones extra
            if "por_ubicacion_extra" in formula and ubicaciones > 1:
                delta = ubicaciones - 1
                add = delta * float(formula["por_ubicacion_extra"])
                extras.append({
                    "concepto": f"{delta} ubicaciones adicionales",
                    "importe": add,
                })
                total_sin_iva += add

            # Sector regulado
            if "por_sector_regulado_extra" in formula and sector_regulado:
                add = float(formula["por_sector_regulado_extra"])
                extras.append({"concepto": "Recargo sector regulado", "importe": add})
                total_sin_iva += add

            # CPDs extra
            if "por_cpd_extra" in formula and cpds > 0:
                add = cpds * float(formula["por_cpd_extra"])
                extras.append({
                    "concepto": f"{cpds} CPDs adicionales",
                    "importe": add,
                })
                total_sin_iva += add

        total_sin_iva = round(total_sin_iva, 2)
        iva_importe = round(total_sin_iva * iva_percent / 100, 2)
        total_con_iva = round(total_sin_iva + iva_importe, 2)

        hitos = []
        for h in model["hitos_pago"]:
            importe = round(total_sin_iva * h["pct"] / 100, 2)
            hitos.append({"nombre": h["nombre"], "pct": h["pct"], "importe": importe})

        return {
            "model_id": model_id,
            "model_nombre": model["nombre"],
            "base": base,
            "extras": extras,
            "total": total_sin_iva,
            "iva_percent": iva_percent,
            "iva_importe": iva_importe,
            "total_con_iva": total_con_iva,
            "hitos": hitos,
            "rango_min": model["rango_min"],
            "rango_max": model["rango_max"],
        }
