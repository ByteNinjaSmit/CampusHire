"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchInput } from "@/components/shared/SearchInput";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useAuditLogs } from "@/lib/api/hooks/admin";
import { formatDate, formatRelativeDate } from "@/lib/format";
import type { AuditLog } from "@/lib/api/types-extra";
import {
  ScrollText,
  Eye,
  Shield,
  Clock,
  Terminal,
  Filter,
} from "lucide-react";

export default function AdminAuditPage() {
  const [entityFilter, setEntityFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useAuditLogs({
    entity_type: entityFilter !== "ALL" ? entityFilter : undefined,
    page,
    page_size: 50,
  });

  const [inspectTarget, setInspectTarget] = useState<AuditLog | null>(null);

  const logs = (data?.items ?? []).filter((item) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      item.action.toLowerCase().includes(q) ||
      item.entity_type.toLowerCase().includes(q) ||
      item.actor_name?.toLowerCase().includes(q) ||
      item.ip?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Institutional Audit Log"
          description="Immutable timeline of security events, administrative approvals, and data mutations across the platform."
        />
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-48">
          <Select value={entityFilter} onValueChange={(v) => { setEntityFilter(v); setPage(1); }}>
            <SelectTrigger className="rounded-xl">
              <SelectValue placeholder="All Entities" />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="ALL">All Entities ({data?.total ?? 0})</SelectItem>
              <SelectItem value="user">Users</SelectItem>
              <SelectItem value="company">Companies</SelectItem>
              <SelectItem value="internship">Internships</SelectItem>
              <SelectItem value="application">Applications</SelectItem>
              <SelectItem value="document">Documents</SelectItem>
              <SelectItem value="policy">Compliance</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="w-full sm:w-72">
          <SearchInput
            value={search}
            onChange={(v) => { setSearch(v); setPage(1); }}
            placeholder="Search action, actor, or entity..."
          />
        </div>
      </div>

      {/* Audit Log Table */}
      {isLoading ? (
        <LoadingTableSkeleton rows={8} />
      ) : logs.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          title="No audit entries"
          description="No recorded audit actions match your filter criteria."
        />
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm overflow-hidden">
          <div className="flex items-center justify-between p-3.5 bg-muted/30 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <span>Action & Entity Target</span>
            <div className="flex items-center gap-16 pr-4">
              <span>Actor</span>
              <span>IP Address</span>
              <span>Timestamp</span>
              <span>Payload</span>
            </div>
          </div>

          {logs.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between p-4 hover:bg-muted/20 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Badge
                  variant="outline"
                  className={`font-mono text-[11px] font-semibold ${
                    item.action.includes("CREATE") || item.action.includes("APPROVE")
                      ? "border-emerald-500/20 text-emerald-600 bg-emerald-500/10"
                      : item.action.includes("DELETE") || item.action.includes("REJECT")
                      ? "border-rose-500/20 text-rose-600 bg-rose-500/10"
                      : "border-primary/20 text-primary bg-primary/10"
                  }`}
                >
                  {item.action}
                </Badge>

                <div>
                  <span className="font-semibold text-sm text-foreground">
                    {item.entity_type}
                  </span>
                  {item.entity_id && (
                    <span className="text-xs text-muted-foreground ml-1.5 font-mono">
                      #{item.entity_id.substring(0, 8)}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-8">
                <span className="text-xs font-medium text-foreground w-28 truncate">
                  {item.actor_name || "System Automated"}
                </span>

                <span className="font-mono text-xs text-muted-foreground hidden md:inline w-24">
                  {item.ip || "127.0.0.1"}
                </span>

                <span className="text-xs text-muted-foreground hidden sm:inline w-32 text-right">
                  {formatDate(item.created_at)}
                </span>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setInspectTarget(item)}
                  className="rounded-xl text-xs gap-1 h-8"
                >
                  <Eye className="size-3.5" /> Inspect
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Inspect State Diff Dialog */}
      <Dialog open={!!inspectTarget} onOpenChange={(o) => !o && setInspectTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Audit Record Inspection</DialogTitle>
            <DialogDescription>
              {inspectTarget?.action} on {inspectTarget?.entity_type} (#{inspectTarget?.entity_id})
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4 text-xs">
            <div className="grid grid-cols-2 gap-4 p-3 rounded-xl bg-muted/20 border border-border/40">
              <div>
                <span className="text-muted-foreground">Actor: </span>
                <strong className="text-foreground">{inspectTarget?.actor_name || "System"}</strong>
              </div>
              <div>
                <span className="text-muted-foreground">Origin IP: </span>
                <strong className="text-foreground">{inspectTarget?.ip || "Localhost"}</strong>
              </div>
              <div>
                <span className="text-muted-foreground">Recorded At: </span>
                <strong className="text-foreground">
                  {inspectTarget?.created_at ? formatDate(inspectTarget.created_at) : ""}
                </strong>
              </div>
              <div>
                <span className="text-muted-foreground">Entity ID: </span>
                <strong className="font-mono text-foreground">{inspectTarget?.entity_id}</strong>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <span className="font-semibold text-muted-foreground uppercase text-[10px]">
                  Before State (Previous)
                </span>
                <pre className="p-3 rounded-xl bg-muted/30 border border-border/40 font-mono text-[11px] overflow-x-auto max-h-56">
                  {inspectTarget?.before ? JSON.stringify(inspectTarget.before, null, 2) : "null (new entity)"}
                </pre>
              </div>

              <div className="space-y-1.5">
                <span className="font-semibold text-muted-foreground uppercase text-[10px]">
                  After State (Mutated)
                </span>
                <pre className="p-3 rounded-xl bg-muted/30 border border-border/40 font-mono text-[11px] overflow-x-auto max-h-56 text-emerald-600 dark:text-emerald-400">
                  {inspectTarget?.after ? JSON.stringify(inspectTarget.after, null, 2) : "null (deleted)"}
                </pre>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button onClick={() => setInspectTarget(null)} className="rounded-xl text-xs">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
