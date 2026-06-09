"use client";

import * as React from "react";
import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, Inbox } from "lucide-react";

import { DataTablePagination } from "@/components/ui/data-table-pagination";
import { DataTableSkeleton } from "@/components/ui/data-table-skeleton";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  searchKey?: keyof TData & string;
  searchPlaceholder?: string;
  loading?: boolean;
  emptyState?: React.ReactNode;
  pageSize?: number;
  pageSizeOptions?: number[];
  onRowClick?: (row: TData) => void;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  searchKey,
  searchPlaceholder = "Buscar…",
  loading = false,
  emptyState,
  pageSize = 10,
  pageSizeOptions = [10, 25, 50, 100],
  onRowClick,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    [],
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters },
    initialState: { pagination: { pageSize } },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  if (loading) {
    return (
      <div className="flex flex-col gap-3">
        {searchKey && (
          <Input placeholder={searchPlaceholder} disabled className="max-w-sm" />
        )}
        <DataTableSkeleton columns={columns.length} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {searchKey && (
        <Input
          placeholder={searchPlaceholder}
          value={
            (table.getColumn(searchKey)?.getFilterValue() as string) ?? ""
          }
          onChange={(e) =>
            table.getColumn(searchKey)?.setFilterValue(e.target.value)
          }
          className="max-w-sm"
        />
      )}

      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="bg-muted/50">
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sortDir = header.column.getIsSorted();
                  // Sub-atom Sesión 3B-2B.2 Phase A.3.X · WCAG button-name
                  // critical fix. Sort/header buttons rendered as icon-only
                  // when columnDef.header is a function returning React node
                  // (no plain string) had NO accessible name → axe critical.
                  // Fallback aria-label: "Ordenar por {column.id}" when
                  // sortable, or "{column.id}" generic otherwise.
                  const headerDef = header.column.columnDef.header;
                  // Sub-atom Sesión 3B-2B.3 Phase C.2 · WCAG button-name fix.
                  // When columnDef.header === "" (e.g. actions column with no
                  // visible header), previous fallback used the empty string as
                  // aria-label → axe critical button-name failure.
                  // Now: empty string headers fall back to column.id (always set).
                  const headerString =
                    typeof headerDef === "string" && headerDef.length > 0
                      ? headerDef
                      : header.column.id;
                  const ariaLabel = canSort
                    ? `Ordenar por ${headerString}`
                    : headerString;
                  return (
                    <TableHead key={header.id} className="text-foreground">
                      {header.isPlaceholder ? null : (
                        <button
                          type="button"
                          aria-label={ariaLabel}
                          onClick={
                            canSort
                              ? header.column.getToggleSortingHandler()
                              : undefined
                          }
                          className={cn(
                            "inline-flex items-center gap-1 font-medium",
                            canSort && "cursor-pointer hover:text-primary",
                          )}
                          disabled={!canSort}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          {canSort && (
                            <span
                              aria-hidden
                              className="text-muted-foreground"
                            >
                              {sortDir === "asc" ? (
                                <ArrowUp className="h-3.5 w-3.5" />
                              ) : sortDir === "desc" ? (
                                <ArrowDown className="h-3.5 w-3.5" />
                              ) : (
                                <ArrowUpDown className="h-3.5 w-3.5 opacity-40" />
                              )}
                            </span>
                          )}
                        </button>
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>

          <TableBody>
            {table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-32 text-center"
                >
                  {emptyState ?? <DefaultEmptyState />}
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  className={cn(onRowClick && "cursor-pointer")}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <DataTablePagination table={table} pageSizeOptions={pageSizeOptions} />
    </div>
  );
}

function DefaultEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-6 text-muted-foreground">
      <Inbox className="h-6 w-6" />
      <p className="text-sm">Sin resultados</p>
    </div>
  );
}
