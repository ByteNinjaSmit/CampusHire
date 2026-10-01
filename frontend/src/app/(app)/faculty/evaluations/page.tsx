"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useEvaluations,
  useEvaluationForms,
  useCreateEvaluationForm,
  useArchiveEvaluationForm,
} from "@/lib/api/hooks/evaluations";
import { formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import {
  Award,
  ClipboardList,
  Plus,
  Trash2,
  FileCheck,
  CheckCircle2,
  ListPlus,
} from "lucide-react";

interface CriterionInput {
  name: string;
  weight: number;
  max_score: number;
}

export default function FacultyEvaluationsPage() {
  const [tab, setTab] = useState<"evaluations" | "forms">("evaluations");

  const { data: evalsData, isLoading: isEvalsLoading } = useEvaluations({ page: 1, page_size: 50 });
  const { data: forms, isLoading: isFormsLoading, refetch: refetchForms } = useEvaluationForms();

  const createForm = useCreateEvaluationForm();
  const archiveForm = useArchiveEvaluationForm();

  // Create form modal state
  const [createOpen, setCreateOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [criteria, setCriteria] = useState<CriterionInput[]>([
    { name: "Technical Competence", weight: 3, max_score: 10 },
    { name: "Problem Solving", weight: 2, max_score: 10 },
    { name: "Communication Skills", weight: 1, max_score: 5 },
  ]);

  const evaluations = evalsData?.items ?? [];

  const handleAddCriterion = () => {
    setCriteria([...criteria, { name: "", weight: 1, max_score: 10 }]);
  };

  const handleRemoveCriterion = (idx: number) => {
    setCriteria(criteria.filter((_, i) => i !== idx));
  };

  const handleUpdateCriterion = (idx: number, field: keyof CriterionInput, val: string | number) => {
    setCriteria(
      criteria.map((c, i) => (i === idx ? { ...c, [field]: val } : c))
    );
  };

  const handleCreateForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      toast.error("Form title is required.");
      return;
    }
    if (criteria.some((c) => !c.name.trim())) {
      toast.error("All criteria must have names.");
      return;
    }

    createForm.mutate(
      {
        name: formName.trim(),
        description: formDesc.trim() || undefined,
        criteria: criteria.map((c, i) => ({
          name: c.name.trim(),
          weight: Number(c.weight) || 1,
          max_score: Number(c.max_score) || 10,
          position: i + 1,
        })),
      },
      {
        onSuccess: () => {
          toast.success("Evaluation rubric created");
          setCreateOpen(false);
          setFormName("");
          setFormDesc("");
          refetchForms();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to create evaluation form")),
      }
    );
  };

  const handleArchiveForm = (id: string) => {
    archiveForm.mutate(id, {
      onSuccess: () => {
        toast.success("Form archived");
        refetchForms();
      },
      onError: (err) => toast.error(errorMessage(err, "Failed to archive form")),
    });
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Evaluation Center"
          description="Assess candidate submissions with standardized weighted rubrics and manage evaluation forms."
        />
        <Button onClick={() => setCreateOpen(true)} className="gap-2 rounded-xl">
          <Plus className="size-4" /> Create Evaluation Rubric
        </Button>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as "evaluations" | "forms")}>
        <TabsList className="bg-muted/60">
          <TabsTrigger value="evaluations" className="gap-2">
            Completed Evaluations ({evaluations.length})
          </TabsTrigger>
          <TabsTrigger value="forms" className="gap-2">
            Rubric Forms ({forms?.length ?? 0})
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Evaluations */}
        <TabsContent value="evaluations" className="pt-4">
          {isEvalsLoading ? (
            <LoadingTableSkeleton rows={4} />
          ) : evaluations.length === 0 ? (
            <EmptyState
              icon={Award}
              title="No evaluations recorded"
              description="Evaluations recorded during candidate review will appear here."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {evaluations.map((ev) => (
                <Card key={ev.id} className="rounded-2xl border-border/60 p-5 shadow-sm space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-base text-foreground">
                        {ev.student?.full_name || "Candidate"}
                      </h4>
                      <p className="text-xs text-muted-foreground">{ev.internship?.title}</p>
                    </div>
                    <Badge variant="outline" className="text-primary font-bold text-sm">
                      {ev.weighted_score}%
                    </Badge>
                  </div>

                  <div className="rounded-xl border bg-muted/20 p-3 space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Rubric</span>
                      <span className="font-medium text-foreground">{ev.form_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Recommendation</span>
                      <span className="font-semibold text-foreground">{ev.recommendation}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Evaluator</span>
                      <span>{ev.evaluator_name}</span>
                    </div>
                  </div>

                  {ev.overall_comments && (
                    <p className="text-xs text-muted-foreground italic line-clamp-2">
                      &ldquo;{ev.overall_comments}&rdquo;
                    </p>
                  )}

                  <div className="flex justify-between text-[11px] text-muted-foreground pt-1 border-t">
                    <span>{formatDate(ev.created_at)}</span>
                    <span className="text-emerald-600 font-medium">Shared with student</span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Tab 2: Rubric Forms */}
        <TabsContent value="forms" className="pt-4">
          {isFormsLoading ? (
            <LoadingTableSkeleton rows={3} />
          ) : !forms || forms.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title="No evaluation forms"
              description="Create a standardized evaluation form with weighted criteria."
            />
          ) : (
            <div className="grid gap-6 sm:grid-cols-2">
              {forms.map((f) => (
                <Card key={f.id} className="rounded-2xl border-border/60 p-5 shadow-sm space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-base text-foreground">{f.name}</h4>
                        {f.is_default && <Badge variant="secondary" className="text-[10px]">Default</Badge>}
                      </div>
                      {f.description && <p className="text-xs text-muted-foreground pt-1">{f.description}</p>}
                    </div>

                    {!f.is_default && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-muted-foreground hover:text-destructive"
                        onClick={() => handleArchiveForm(f.id)}
                        title="Archive rubric"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    )}
                  </div>

                  <div className="space-y-2 rounded-xl border bg-muted/20 p-3.5 text-xs">
                    <span className="font-semibold text-muted-foreground uppercase text-[10px]">Criteria Rubric</span>
                    <div className="divide-y divide-border/60">
                      {f.criteria?.map((c) => (
                        <div key={c.id} className="flex justify-between py-1.5">
                          <span className="text-foreground">{c.name}</span>
                          <span className="text-muted-foreground font-mono">
                            Max: {c.max_score} • W: {c.weight}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Create Rubric Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Create Evaluation Rubric</DialogTitle>
            <DialogDescription>
              Define scoring criteria and weights for candidate evaluations.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateForm} className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="formName">Form Title</Label>
              <Input
                id="formName"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Backend Engineering Assessment"
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="formDesc">Description</Label>
              <Input
                id="formDesc"
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                placeholder="Brief description for evaluators"
                className="rounded-xl"
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Evaluation Criteria</Label>
                <Button type="button" variant="outline" size="sm" onClick={handleAddCriterion} className="rounded-xl text-xs gap-1">
                  <Plus className="size-3.5" /> Add Criterion
                </Button>
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {criteria.map((c, idx) => (
                  <div key={idx} className="flex items-center gap-2 rounded-xl border p-2 bg-card">
                    <Input
                      value={c.name}
                      onChange={(e) => handleUpdateCriterion(idx, "name", e.target.value)}
                      placeholder="Criterion Name"
                      className="h-8 rounded-lg text-xs flex-1"
                    />
                    <div className="flex items-center gap-1 w-20">
                      <span className="text-[10px] text-muted-foreground">W:</span>
                      <Input
                        type="number"
                        min="1"
                        max="10"
                        value={c.weight}
                        onChange={(e) => handleUpdateCriterion(idx, "weight", Number(e.target.value))}
                        className="h-8 rounded-lg text-xs"
                      />
                    </div>
                    <div className="flex items-center gap-1 w-24">
                      <span className="text-[10px] text-muted-foreground">Max:</span>
                      <Input
                        type="number"
                        min="1"
                        max="100"
                        value={c.max_score}
                        onChange={(e) => handleUpdateCriterion(idx, "max_score", Number(e.target.value))}
                        className="h-8 rounded-lg text-xs"
                      />
                    </div>
                    {criteria.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-7 text-muted-foreground hover:text-destructive"
                        onClick={() => handleRemoveCriterion(idx)}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createForm.isPending} className="rounded-xl">
                Create Rubric
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
