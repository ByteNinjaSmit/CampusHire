"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchInput } from "@/components/shared/SearchInput";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useInternships, useToggleSaveInternship, useInternshipFacets } from "@/lib/api/hooks/internships";
import { useAuth } from "@/providers/AuthProvider";
import { formatCurrency, formatRelativeDate, formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { Internship, WorkMode } from "@/lib/api/types";
import {
  Briefcase,
  Building2,
  MapPin,
  Calendar,
  Clock,
  Heart,
  LayoutGrid,
  List,
  Sparkles,
  ArrowRight,
  Filter,
} from "lucide-react";

export default function InternshipsExplorerPage() {
  const { user } = useAuth();
  const isStudent = user?.role === "STUDENT";

  const [search, setSearch] = useState("");
  const [workMode, setWorkMode] = useState<string>("ALL");
  const [selectedDept, setSelectedDept] = useState<string>("ALL");
  const [sort, setSort] = useState<string>("newest");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [page, setPage] = useState(1);

  const { data: facets } = useInternshipFacets();

  const { data, isLoading } = useInternships({
    q: search || undefined,
    work_mode: workMode !== "ALL" ? (workMode as WorkMode) : undefined,
    domain: selectedDept !== "ALL" ? [selectedDept] : undefined,
    page,
    page_size: 18,
  });

  const toggleSave = useToggleSaveInternship();

  const internships = data?.items ?? [];

  const handleToggleSave = (id: string, currentlySaved: boolean, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isStudent) {
      toast.info("Only students can bookmark internships.");
      return;
    }
    toggleSave.mutate(
      { id, saved: currentlySaved },
      {
        onSuccess: () => {
          toast.success(currentlySaved ? "Removed from saved" : "Saved to your bookmarks");
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to update bookmark")),
      }
    );
  };

  const domains = (facets?.domains ?? []).map((d) => d.value);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Explore Internships"
          description="Browse campus recruitment opportunities and apply with your verified profile."
        />
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Button
            variant={viewMode === "grid" ? "default" : "outline"}
            size="icon"
            onClick={() => setViewMode("grid")}
            className="size-9 rounded-xl"
            title="Grid view"
          >
            <LayoutGrid className="size-4" />
          </Button>
          <Button
            variant={viewMode === "list" ? "default" : "outline"}
            size="icon"
            onClick={() => setViewMode("list")}
            className="size-9 rounded-xl"
            title="List view"
          >
            <List className="size-4" />
          </Button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-card p-4 shadow-sm backdrop-blur-sm sm:flex-row sm:items-center">
        <div className="flex-1">
          <SearchInput
            value={search}
            onChange={(v) => {
              setSearch(v);
              setPage(1);
            }}
            placeholder="Search titles, skills, or companies..."
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="w-36">
            <Select
              value={workMode}
              onValueChange={(v) => {
                setWorkMode(v);
                setPage(1);
              }}
            >
              <SelectTrigger className="h-10 rounded-xl text-xs">
                <SelectValue placeholder="Work Mode" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                <SelectItem value="ALL">All Modes</SelectItem>
                <SelectItem value="REMOTE">Remote</SelectItem>
                <SelectItem value="HYBRID">Hybrid</SelectItem>
                <SelectItem value="ONSITE">On-site</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="w-44">
            <Select
              value={selectedDept}
              onValueChange={(v) => {
                setSelectedDept(v);
                setPage(1);
              }}
            >
              <SelectTrigger className="h-10 rounded-xl text-xs">
                <SelectValue placeholder="Domain" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                <SelectItem value="ALL">All Domains</SelectItem>
                {domains.map((dept) => (
                  <SelectItem key={dept} value={dept}>
                    {dept}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Internship Cards / List */}
      {isLoading ? (
        <LoadingCardGrid count={6} />
      ) : internships.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No internships found"
          description="Try clearing your search query or adjusting your department and work mode filters."
          action={
            <Button
              variant="outline"
              onClick={() => {
                setSearch("");
                setWorkMode("ALL");
                setSelectedDept("ALL");
              }}
              className="rounded-xl"
            >
              Reset Filters
            </Button>
          }
        />
      ) : viewMode === "grid" ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {internships.map((item) => (
            <Card
              key={item.id}
              className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border-border/60 bg-card transition-all duration-200 hover:-translate-y-1 hover:border-primary/40 hover:shadow-md"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold shadow-xs">
                      {item.company?.name?.[0]?.toUpperCase() || <Building2 className="size-6" />}
                    </div>
                    <div>
                      <h4 className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">
                        {item.company?.name || "Campus Placement"}
                      </h4>
                      <CardTitle className="line-clamp-1 text-base group-hover:text-primary transition-colors">
                        <Link href={`/internships/${item.id}`}>{item.title}</Link>
                      </CardTitle>
                    </div>
                  </div>

                  {isStudent && (
                    <button
                      type="button"
                      onClick={(e) => handleToggleSave(item.id, !!item.is_saved, e)}
                      className={`rounded-full p-2 transition-colors hover:bg-muted ${
                        item.is_saved ? "text-rose-500" : "text-muted-foreground hover:text-rose-500"
                      }`}
                      title={item.is_saved ? "Remove bookmark" : "Save internship"}
                    >
                      <Heart className={`size-4 ${item.is_saved ? "fill-rose-500" : ""}`} />
                    </button>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-1.5 pt-3">
                  <Badge variant="secondary" className="text-xs">
                    {item.work_mode}
                  </Badge>
                  {item.location && (
                    <Badge variant="outline" className="gap-1 text-xs">
                      <MapPin className="size-3 text-muted-foreground" />
                      {item.location}
                    </Badge>
                  )}
                  <Badge variant="outline" className="text-xs text-emerald-600 dark:text-emerald-400 border-emerald-500/20">
                    {item.stipend_monthly ? `${formatCurrency(item.stipend_monthly)} / mo` : "Unpaid"}
                  </Badge>
                </div>
              </CardHeader>

              <CardContent className="space-y-3 pb-3">
                <p className="line-clamp-2 text-xs text-muted-foreground leading-relaxed">
                  {item.domain} • {item.work_mode} • {item.duration_weeks} Weeks
                </p>

                {item.skills && item.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {item.skills.slice(0, 3).map((skill) => (
                      <span
                        key={skill}
                        className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
                      >
                        {skill}
                      </span>
                    ))}
                    {item.skills.length > 3 && (
                      <span className="text-[11px] text-muted-foreground self-center">
                        +{item.skills.length - 3} more
                      </span>
                    )}
                  </div>
                )}
              </CardContent>

              <CardFooter className="flex items-center justify-between border-t border-border/40 pt-3 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Clock className="size-3.5" />
                  <span>Due {formatDate(item.application_deadline)}</span>
                </div>

                <Button size="sm" variant="ghost" asChild className="gap-1 text-xs font-medium hover:text-primary">
                  <Link href={`/internships/${item.id}`}>
                    Details <ArrowRight className="size-3.5" />
                  </Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : (
        <div className="divide-y divide-border/60 rounded-2xl border border-border/60 bg-card">
          {internships.map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-4 p-5 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex items-start gap-4">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold shadow-xs">
                  {item.company?.name?.[0]?.toUpperCase() || <Building2 className="size-6" />}
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase">
                      {item.company?.name}
                    </span>
                    <Badge variant="secondary" className="text-[10px]">
                      {item.work_mode}
                    </Badge>
                  </div>
                  <h3 className="font-semibold text-base text-foreground hover:text-primary">
                    <Link href={`/internships/${item.id}`}>{item.title}</Link>
                  </h3>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    {item.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="size-3" /> {item.location}
                      </span>
                    )}
                    <span>•</span>
                    <span className="font-medium text-emerald-600 dark:text-emerald-400">
                      {item.stipend_monthly ? `${formatCurrency(item.stipend_monthly)} / mo` : "Unpaid"}
                    </span>
                    <span>•</span>
                    <span>Deadline: {formatDate(item.application_deadline)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 self-end sm:self-center">
                {isStudent && (
                  <button
                    type="button"
                    onClick={(e) => handleToggleSave(item.id, !!item.is_saved, e)}
                    className={`rounded-full p-2 transition-colors hover:bg-muted ${
                      item.is_saved ? "text-rose-500" : "text-muted-foreground hover:text-rose-500"
                    }`}
                  >
                    <Heart className={`size-4 ${item.is_saved ? "fill-rose-500" : ""}`} />
                  </button>
                )}

                <Button size="sm" asChild className="rounded-xl gap-1">
                  <Link href={`/internships/${item.id}`}>
                    View Posting <ArrowRight className="size-3.5" />
                  </Link>
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded-xl"
          >
            Previous
          </Button>
          <span className="text-xs text-muted-foreground">
            Page {page} of {data.pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.pages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-xl"
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
