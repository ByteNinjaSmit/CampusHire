"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { RatingDisplay, RatingInput } from "@/components/shared/Rating";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  useStudentFeedback,
  useCompanyFeedback,
  useRespondToStudentFeedback,
} from "@/lib/api/hooks/feedback";
import { useAuth } from "@/providers/AuthProvider";
import { formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { StudentFeedback } from "@/lib/api/types";
import { MessageSquareText, Reply, Building2, Star, User, Send } from "lucide-react";

export default function CompanyFeedbackPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<"received" | "interns">("received");

  const companyId = user?.company?.company_id;

  const { data: studentFbData, isLoading: isStudentFbLoading, refetch: refetchStudentFb } = useStudentFeedback({
    company_id: companyId,
    page: 1,
    page_size: 50,
  });

  const { data: companyFbData, isLoading: isCompanyFbLoading } = useCompanyFeedback({
    page: 1,
    page_size: 50,
  });

  const respondToFeedback = useRespondToStudentFeedback();

  // Response Dialog State
  const [respondTarget, setRespondTarget] = useState<StudentFeedback | null>(null);
  const [responseText, setResponseText] = useState("");

  const studentReviews = studentFbData?.items ?? [];
  const internEvaluations = companyFbData?.items ?? [];

  const handleRespond = (e: React.FormEvent) => {
    e.preventDefault();
    if (!respondTarget || !responseText.trim()) return;

    respondToFeedback.mutate(
      { id: respondTarget.id, body: responseText.trim() },
      {
        onSuccess: () => {
          toast.success("Employer response published successfully");
          setRespondTarget(null);
          setResponseText("");
          refetchStudentFb();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to submit response")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Company Feedback Center"
          description="View student reviews, monitor corporate ratings, and manage intern exit evaluations."
        />

        <Tabs value={tab} onValueChange={(v) => setTab(v as "received" | "interns")}>
          <TabsList className="rounded-xl">
            <TabsTrigger value="received" className="rounded-lg text-xs gap-1.5">
              <Star className="size-3.5" /> Student Reviews ({studentReviews.length})
            </TabsTrigger>
            <TabsTrigger value="interns" className="rounded-lg text-xs gap-1.5">
              <User className="size-3.5" /> Intern Appraisals ({internEvaluations.length})
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {tab === "received" ? (
        isStudentFbLoading ? (
          <LoadingTableSkeleton rows={4} />
        ) : studentReviews.length === 0 ? (
          <EmptyState
            icon={MessageSquareText}
            title="No Student Reviews"
            description="Reviews submitted by students upon completing internships with your company will be displayed here."
          />
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {studentReviews.map((rev) => (
              <Card key={rev.id} className="rounded-2xl border-border/60 shadow-sm p-6 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-base text-foreground">
                      {rev.internship?.title || "Internship"}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      By: {rev.student_name || "Verified Student (Anonymous)"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 rounded-lg bg-amber-500/10 px-2.5 py-1 text-amber-600 font-bold text-sm">
                    <Star className="size-3.5 fill-current" />
                    <span>{rev.overall?.toFixed(1) || "5.0"}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs bg-muted/20 p-3 rounded-xl">
                  <div>
                    <span className="text-muted-foreground">Culture: </span>
                    <strong className="text-foreground">{rev.company_culture} / 5</strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Mentorship: </span>
                    <strong className="text-foreground">{rev.mentorship} / 5</strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Learning: </span>
                    <strong className="text-foreground">{rev.technical_learning} / 5</strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Environment: </span>
                    <strong className="text-foreground">{rev.work_environment} / 5</strong>
                  </div>
                </div>

                {rev.comments && (
                  <p className="text-xs text-foreground leading-relaxed">
                    {rev.comments}
                  </p>
                )}

                {rev.suggestions && (
                  <div className="text-xs text-muted-foreground bg-muted/30 p-2.5 rounded-lg">
                    <span className="font-semibold text-foreground">Suggestions for employer: </span>
                    {rev.suggestions}
                  </div>
                )}

                {rev.response_body ? (
                  <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold text-primary">
                      <Reply className="size-3.5" /> Employer Response
                    </div>
                    <p className="text-foreground">{rev.response_body}</p>
                    <p className="text-[10px] text-muted-foreground pt-1">
                      Responded {rev.responded_at ? formatDate(rev.responded_at) : ""}
                    </p>
                  </div>
                ) : (
                  <div className="pt-2 flex justify-end">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setRespondTarget(rev);
                        setResponseText("");
                      }}
                      className="rounded-xl text-xs gap-1.5"
                    >
                      <Reply className="size-3.5" /> Respond to Review
                    </Button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )
      ) : isCompanyFbLoading ? (
          <LoadingTableSkeleton rows={3} />
        ) : internEvaluations.length === 0 ? (
          <EmptyState
            icon={User}
            title="No Intern Appraisals"
            description="Appraisals given to student interns at the end of their placements will appear here."
          />
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {internEvaluations.map((appr) => (
              <Card key={appr.id} className="rounded-2xl border-border/60 shadow-sm p-6 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-base text-foreground">
                      {appr.student?.full_name || "Student Intern"}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {appr.internship?.title || "Role"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 rounded-lg bg-primary/10 px-2.5 py-1 text-primary font-bold text-xs">
                    <span>Avg {appr.average?.toFixed(1) || "5.0"} / 5</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs bg-muted/20 p-3 rounded-xl">
                  <div>
                    <span className="text-muted-foreground">Technical Skills: </span>
                    <strong className="text-foreground">{appr.technical_skills} / 5</strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Soft Skills: </span>
                    <strong className="text-foreground">{appr.soft_skills} / 5</strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Teamwork: </span>
                    <strong className="text-foreground">{appr.teamwork} / 5</strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Hire Likelihood: </span>
                    <strong className="text-foreground">{appr.hire_likelihood} / 5</strong>
                  </div>
                </div>

                {appr.strengths && (
                  <p className="text-xs text-muted-foreground">
                    <strong className="text-foreground">Key Strengths: </strong>
                    {appr.strengths}
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}

      {/* Response Modal */}
      <Dialog open={!!respondTarget} onOpenChange={(o) => !o && setRespondTarget(null)}>
        <DialogContent className="rounded-2xl sm:max-w-md">
          <form onSubmit={handleRespond}>
            <DialogHeader>
              <DialogTitle>Respond to Student Review</DialogTitle>
              <DialogDescription>
                Post an official employer response to the student&apos;s feedback.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="respText">Response Message</Label>
                <Textarea
                  id="respText"
                  rows={4}
                  value={responseText}
                  onChange={(e) => setResponseText(e.target.value)}
                  placeholder="Thank the student for their feedback and share notes on their internship experience..."
                  required
                  className="rounded-xl"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setRespondTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={respondToFeedback.isPending} className="rounded-xl gap-1.5">
                <Send className="size-3.5" />
                {respondToFeedback.isPending ? "Submitting..." : "Publish Response"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
