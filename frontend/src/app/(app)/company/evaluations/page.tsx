"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  useEvaluations,
  useEvaluationForms,
} from "@/lib/api/hooks/evaluations";
import { formatDate } from "@/lib/format";
import {
  Award,
  ClipboardList,
  CheckCircle2,
  User,
  Star,
  FileCheck,
} from "lucide-react";

export default function CompanyEvaluationsPage() {
  const [tab, setTab] = useState<"evaluations" | "forms">("evaluations");

  const { data: evalsData, isLoading: isEvalsLoading } = useEvaluations({ page: 1, page_size: 50 });
  const { data: forms, isLoading: isFormsLoading } = useEvaluationForms();

  const evaluations = evalsData?.items ?? [];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Candidate Evaluations & Scorecards"
          description="Review rubric evaluations, candidate assessment scores, and hiring recommendations."
        />

        <Tabs value={tab} onValueChange={(v) => setTab(v as "evaluations" | "forms")}>
          <TabsList className="rounded-xl">
            <TabsTrigger value="evaluations" className="rounded-lg text-xs gap-1.5">
              <Award className="size-3.5" /> Evaluations ({evaluations.length})
            </TabsTrigger>
            <TabsTrigger value="forms" className="rounded-lg text-xs gap-1.5">
              <ClipboardList className="size-3.5" /> Rubric Forms ({forms?.length || 0})
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {tab === "evaluations" ? (
        isEvalsLoading ? (
          <LoadingTableSkeleton rows={4} />
        ) : evaluations.length === 0 ? (
          <EmptyState
            icon={Award}
            title="No evaluations submitted"
            description="Evaluations scored during candidate reviews will appear here."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {evaluations.map((ev) => (
              <Card key={ev.id} className="rounded-2xl border-border/60 shadow-sm p-5 space-y-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <h3 className="font-semibold text-base text-foreground">
                      {ev.application?.student?.full_name || "Candidate"}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {ev.application?.internship?.title || "Internship Role"}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className={`text-xs font-semibold ${
                      ev.recommendation === "STRONG_YES" || ev.recommendation === "YES"
                        ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                        : ev.recommendation === "MAYBE"
                        ? "bg-amber-500/10 text-amber-600 border-amber-500/20"
                        : "bg-rose-500/10 text-rose-600 border-rose-500/20"
                    }`}
                  >
                    {ev.recommendation.replace("_", " ")}
                  </Badge>
                </div>

                <div className="flex items-center justify-between rounded-xl bg-primary/5 p-3 text-xs">
                  <span className="text-muted-foreground font-medium">Weighted Score</span>
                  <span className="text-lg font-bold text-primary">
                    {ev.weighted_score != null ? `${ev.weighted_score.toFixed(1)} / 100` : "N/A"}
                  </span>
                </div>

                {ev.comments && (
                  <p className="text-xs text-muted-foreground line-clamp-3 bg-muted/20 p-2.5 rounded-lg italic">
                    &ldquo;{ev.comments}&rdquo;
                  </p>
                )}

                <div className="flex items-center justify-between pt-3 border-t border-border/40 text-[11px] text-muted-foreground">
                  <span>Evaluated {formatDate(ev.created_at)}</span>
                  <span className="font-medium text-foreground">
                    By: {ev.evaluator?.full_name || "Recruiter"}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        )
      ) : isFormsLoading ? (
          <LoadingTableSkeleton rows={3} />
        ) : !forms || forms.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="No Evaluation Forms"
            description="Institutional rubrics configured by faculty/admin will appear here."
          />
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {forms.map((f) => (
              <Card key={f.id} className="rounded-2xl border-border/60 shadow-sm p-6 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-lg text-foreground">{f.title}</h3>
                    {f.description && (
                      <p className="text-xs text-muted-foreground mt-1">{f.description}</p>
                    )}
                  </div>
                  {f.is_default && (
                    <Badge variant="secondary" className="text-xs">
                      Default Template
                    </Badge>
                  )}
                </div>

                <div className="space-y-2 pt-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Scoring Criteria ({f.criteria?.length || 0})
                  </h4>
                  <div className="space-y-2">
                    {f.criteria?.map((c) => (
                      <div
                        key={c.id}
                        className="flex items-center justify-between text-xs p-2 rounded-lg bg-muted/30"
                      >
                        <span className="font-medium text-foreground">{c.name}</span>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <span>Max: {c.max_score} pts</span>
                          <span>•</span>
                          <span>Weight: {c.weight}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
    </div>
  );
}
