"use client";

import Link from "next/link";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingCardGrid } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useSavedInternships, useToggleSaveInternship } from "@/lib/api/hooks/internships";
import { formatCurrency, formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import { Heart, Building2, MapPin, Clock, ArrowRight, Compass } from "lucide-react";

export default function SavedInternshipsPage() {
  const { data, isLoading } = useSavedInternships({ page: 1, page_size: 50 });
  const toggleSave = useToggleSaveInternship();

  const savedInternships = data?.items ?? [];

  const handleRemove = (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    toggleSave.mutate(
      { id, saved: true },
      {
        onSuccess: () => toast.success("Removed from saved bookmarks"),
        onError: (err) => toast.error(errorMessage(err, "Failed to remove bookmark")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Saved Internships"
          description="Keep track of internship opportunities you are interested in applying to later."
        />
        <Button asChild className="rounded-xl gap-2">
          <Link href="/internships">
            <Compass className="size-4" /> Discover More
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <LoadingCardGrid count={3} />
      ) : savedInternships.length === 0 ? (
        <EmptyState
          icon={Heart}
          title="No saved internships"
          description="Click the bookmark heart icon on any internship posting to save it for quick reference."
          action={
            <Button asChild className="rounded-xl">
              <Link href="/internships">Browse Internships</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {savedInternships.map((item) => (
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

                  <button
                    type="button"
                    onClick={(e) => handleRemove(item.id, e)}
                    className="rounded-full p-2 text-rose-500 transition-colors hover:bg-muted"
                    title="Remove from saved"
                  >
                    <Heart className="size-4 fill-rose-500" />
                  </button>
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
                <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                  {item.skills?.slice(0, 3).map((s) => (
                    <Badge key={s} variant="secondary" className="text-[10px]">
                      {s}
                    </Badge>
                  ))}
                  <span>• {item.duration_weeks} Weeks</span>
                </div>
              </CardContent>

              <CardFooter className="flex items-center justify-between border-t border-border/40 pt-3 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Clock className="size-3.5" />
                  <span>Due {formatDate(item.application_deadline)}</span>
                </div>

                <Button size="sm" asChild className="gap-1 text-xs font-medium rounded-xl">
                  <Link href={`/internships/${item.id}/apply`}>
                    Apply Now <ArrowRight className="size-3.5" />
                  </Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
