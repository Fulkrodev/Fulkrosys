/**
 * Matriz adaptación m_live_records · sub-atom 1.C.C.B.fix v3.9.
 *
 * Materializa Anexo K plan v3.9 (matriz per category) · R28 sostener.
 *
 * ⚠️ DRY WARNING · MUST mirror `backend/app/motors/m_live_records/constants.py`.
 * Si modificas esta matriz, actualiza el backend al mismo tiempo. Test backend
 * `test_register_categories.py::test_categories_consistency` valida counts
 * pero NO valida sync frontend↔backend automático (TODO future: codegen).
 *
 * Source authoritative:
 *   - ENS RD 311/2022 Anexo II (73 medidas)
 *   - Plan FULKRO v3.8 §32 Anexo K.2 (counts: B=17 · M=24 · A=26)
 */

export type CategoryEns = "BASICA" | "MEDIA" | "ALTA";

const ALL: ReadonlySet<CategoryEns> = new Set<CategoryEns>([
  "BASICA",
  "MEDIA",
  "ALTA",
]);
const MA: ReadonlySet<CategoryEns> = new Set<CategoryEns>(["MEDIA", "ALTA"]);
const A_ONLY: ReadonlySet<CategoryEns> = new Set<CategoryEns>(["ALTA"]);

export const REGISTER_TYPE_REQUIRED_CATEGORIES: Record<
  string,
  ReadonlySet<CategoryEns>
> = {
  // Bloque activos · TODOS niveles
  "E-300": ALL,
  "E-301": ALL,
  "E-302": ALL,
  // Bloque personas · TODOS niveles
  "E-303": ALL,
  "E-304": ALL,
  // Bloque incidentes
  "E-305": ALL,
  "E-306": MA,
  "E-307": ALL,
  // Bloque cambios
  "E-308": ALL,
  "E-309": MA,
  "E-310": ALL,
  // Bloque proveedores
  "E-311": ALL,
  "E-312": MA,
  "E-313": ALL,
  // Bloque backup
  "E-314": ALL,
  "E-315": ALL,
  "E-316": MA,
  // Bloque continuidad
  "E-317": MA,
  "E-318": A_ONLY,
  "E-319": A_ONLY,
  // Bloque auditoría
  "E-320": ALL,
  "E-321": MA,
  "E-322": ALL,
  // Bloque comité
  "E-323": ALL,
  "E-324": ALL,
  "E-325": MA,
} as const;

export function isRegisterRequiredForCategory(
  registerType: string,
  category: CategoryEns,
): boolean {
  const required = REGISTER_TYPE_REQUIRED_CATEGORIES[registerType];
  if (!required) return false;
  return required.has(category);
}

export function getRequiredRegistersForCategory(
  category: CategoryEns,
): string[] {
  return Object.entries(REGISTER_TYPE_REQUIRED_CATEGORIES)
    .filter(([, cats]) => cats.has(category))
    .map(([rt]) => rt)
    .sort();
}

export function getCategoriesForRegister(
  registerType: string,
): ReadonlySet<CategoryEns> {
  return (
    REGISTER_TYPE_REQUIRED_CATEGORIES[registerType] ??
    (new Set<CategoryEns>() as ReadonlySet<CategoryEns>)
  );
}

export const COUNTS_PER_CATEGORY: Record<CategoryEns, number> = {
  BASICA: 17,
  MEDIA: 24,
  ALTA: 26,
};
