"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type RowSelectionState,
} from "@tanstack/react-table";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { EmptyState } from "./EmptyState";
import { TableSkeleton } from "./LoadingSkeletons";

export interface DataTableProps<T> {
  columns: ColumnDef<T, unknown>[];
  data: T[];
  /** Total rows on the server (for pagination). Defaults to data.length. */
  total?: number;
  /** 1-based page number. */
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  selectable?: boolean;
  onSelectionChange?: (rows: T[]) => void;
  /** Unique row id; defaults to `row.id` if present, otherwise the index. */
  getRowId?: (row: T, index: number) => string;
  onRowClick?: (row: T) => void;
  toolbar?: ReactNode;
  loading?: boolean;
  emptyState?: ReactNode;
  className?: string;
  /** Slot rendered between the toolbar and the table, e.g. BulkActionBar. */
  bulkBar?: ReactNode;
}

export function DataTable<T>({
  columns,
  data,
  total,
  page = 1,
  pageSize = 20,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50, 100],
  selectable,
  onSelectionChange,
  getRowId,
  onRowClick,
  toolbar,
  loading,
  emptyState,
  className,
  bulkBar,
}: DataTableProps<T>) {
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const rowCount = total ?? data.length;
  const pageCount = Math.max(1, Math.ceil(rowCount / pageSize));

  const allColumns = useMemo<ColumnDef<T, unknown>[]>(() => {
    if (!selectable) return columns;
    const selectCol: ColumnDef<T, unknown> = {
      id: "__select",
      enableSorting: false,
      header: ({ table }) => (
        <Checkbox
          aria-label="Select all rows"
          checked={table.getIsAllPageRowsSelected() ? true : table.getIsSomePageRowsSelected() ? "indeterminate" : false}
          onCheckedChange={(v) => table.toggleAllPageRowsSelected(v === true)}
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          aria-label="Select row"
          checked={row.getIsSelected()}
          onClick={(e) => e.stopPropagation()}
          onCheckedChange={(v) => row.toggleSelected(v === true)}
        />
      ),
    };
    return [selectCol, ...columns];
  }, [columns, selectable]);

  const table = useReactTable({
    data,
    columns: allColumns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    rowCount,
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
    enableRowSelection: !!selectable,
    getRowId: getRowId ?? ((row, i) => {
      const id = (row as { id?: unknown }).id;
      return typeof id === "string" || typeof id === "number" ? String(id) : String(i);
    }),
  });

  // Clear selection whenever the page data changes.
  useEffect(() => {
    setRowSelection({});
  }, [data]);

  const selectedRows = table.getSelectedRowModel().rows;
  useEffect(() => {
    onSelectionChange?.(selectedRows.map((r) => r.original));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rowSelection]);

  const from = rowCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, rowCount);

  return (
    <div className={cn("space-y-3", className)}>
      {toolbar && <div className="flex flex-wrap items-center gap-2">{toolbar}</div>}
      {bulkBar}
      <div className="card-surface overflow-hidden">
        {loading && data.length === 0 ? (
          <TableSkeleton cols={Math.max(3, columns.length)} />
        ) : data.length === 0 ? (
          <div className="p-4">{emptyState ?? <EmptyState title="Nothing here yet" description="No records match your filters." compact />}</div>
        ) : (
          <div className={cn("overflow-x-auto transition-opacity", loading && "opacity-60")}>
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((hg) => (
                  <TableRow key={hg.id} className="bg-muted/40 hover:bg-muted/40">
                    {hg.headers.map((h) => (
                      <TableHead key={h.id} className={cn("whitespace-nowrap text-xs font-semibold uppercase tracking-wide text-muted-foreground", h.id === "__select" && "w-10")}>
                        {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    data-state={row.getIsSelected() ? "selected" : undefined}
                    className={cn(onRowClick && "cursor-pointer")}
                    onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        {rowCount > 0 && onPageChange && (
          <div className="flex flex-col items-center justify-between gap-3 border-t px-4 py-3 text-sm sm:flex-row">
            <div className="text-muted-foreground">
              Showing <span className="font-medium text-foreground">{from}</span> to <span className="font-medium text-foreground">{to}</span> of{" "}
              <span className="font-medium text-foreground">{rowCount}</span>
            </div>
            <div className="flex items-center gap-3">
              {onPageSizeChange && (
                <Select value={String(pageSize)} onValueChange={(v) => onPageSizeChange(Number(v))}>
                  <SelectTrigger size="sm" className="w-[88px] rounded-lg" aria-label="Rows per page">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {pageSizeOptions.map((o) => (
                      <SelectItem key={o} value={String(o)}>
                        {o} / page
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <div className="flex items-center gap-1">
                <Button variant="outline" size="icon-sm" aria-label="First page" disabled={page <= 1} onClick={() => onPageChange(1)}>
                  <ChevronsLeft />
                </Button>
                <Button variant="outline" size="icon-sm" aria-label="Previous page" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
                  <ChevronLeft />
                </Button>
                <span className="px-2 text-muted-foreground">
                  Page <span className="font-medium text-foreground">{page}</span> of {pageCount}
                </span>
                <Button variant="outline" size="icon-sm" aria-label="Next page" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>
                  <ChevronRight />
                </Button>
                <Button variant="outline" size="icon-sm" aria-label="Last page" disabled={page >= pageCount} onClick={() => onPageChange(pageCount)}>
                  <ChevronsRight />
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
