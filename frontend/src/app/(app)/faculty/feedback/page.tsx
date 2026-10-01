"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { RatingDisplay, RatingInput } from "@/components/shared/Rating";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingTableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  useStudentFeedback,
  useFacultyFeedback,
  useRespondToStudentFeedback,
  useCreateFacultyFeedback,
} from "@/lib/api/hooks/feedback";
import { useInternships } from "@/lib/api/hooks/internships";
import { formatDate } from "@/lib/format";
import { toast } from "sonner";
import { errorMessage } from "@/lib/forms";
import type { StudentFeedback } from "@/lib/api/types";
import { MessageSquareText, Reply, Send, Building2, Star } from "lucide-react";

export default function FacultyFeedbackPage() {
  const [tab, setTab] = useState<"student" | "my">("student");

  const { data: studentFbData, isLoading: isStudentFbLoading, refetch: refetchStudentFb } = useStudentFeedback({
    page: 1,
    page_size: 50,
  });
  const { data: facultyFbData, isLoading: isFacultyFbLoading, refetch: refetchFacultyFb } = useFacultyFeedback({
    page: 1,
    page_size: 50,
  });
  const { data: myInternships } = useInternships({ page_size: 50 });

  const respondToFeedback = useRespondToStudentFeedback();
  const createFacultyFb = useCreateFacultyFeedback();

  // Response Dialog
  const [respondTarget, setRespondTarget] = useState<StudentFeedback | null>(null);
  const [responseText, setResponseText] = useState("");

  // Create Faculty Feedback Dialog
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedInternshipId, setSelectedInternshipId] = useState("");
  const [companyRating, setCompanyRating] = useState(5);
  const [studentPreparationRating, setStudentPreparationRating] = useState(5);
  const [curriculumRelevanceRating, setCurriculumRelevanceRating] = useState(5);
  const [facultyComments, setFacultyComments] = useState("");

  const studentReviews = studentFbData?.items ?? [];
  const facultyReviews = facultyFbData?.items ?? [];
  const postings = myInternships?.items ?? [];

  const handleRespond = (e: React.FormEvent) => {
    e.preventDefault();
    if (!respondTarget || !responseText.trim()) return;

    respondToFeedback.mutate(
      { id: respondTarget.id, body: responseText.trim() },
      {
        onSuccess: () => {
          toast.success("Response recorded successfully");
          setRespondTarget(null);
          setResponseText("");
          refetchStudentFb();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to submit response")),
      }
    );
  };

  const handleCreateFacultyFeedback = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInternshipId) {
      toast.error("Please select an internship.");
      return;
    }

    createFacultyFb.mutate(
      {
        internship_id: selectedInternshipId,
        company_cooperation_rating: companyRating,
        student_preparation_rating: studentPreparationRating,
        curriculum_relevance_rating: curriculumRelevanceRating,
        comments: facultyComments.trim() || "Faculty placement review completed",
      },
      {
        onSuccess: () => {
          toast.success("Faculty feedback submitted");
          setCreateOpen(false);
          setFacultyComments("");
          refetchFacultyFb();
        },
        onError: (err) => toast.error(errorMessage(err, "Failed to submit feedback")),
      }
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Feedback & Reviews"
          description="Review student experiences on your postings, post corporate responses, and evaluate partner programs."
        />
        <Button onClick={() => setCreateOpen(true)} className="gap-2 rounded-xl">
          <Send className="size-4" /> Submit Institutional Feedback
        </Button>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as "student" | "my")}>
        <TabsList className="bg-muted/60">
          <TabsTrigger value="student" className="gap-2">
            Student Reviews ({studentReviews.length})
          </TabsTrigger>
          <TabsTrigger value="my" className="gap-2">
            Faculty Program Evaluations ({facultyReviews.length})
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Student Reviews on Postings */}
        <TabsContent value="student" className="pt-4">
          {isStudentFbLoading ? (
            <LoadingTableSkeleton rows={4} />
          ) : studentReviews.length === 0 ? (
            <EmptyState
              icon={MessageSquareText}
              title="No student reviews yet"
              description="Student evaluations for your internships will be displayed here."
            />
          ) : (
            <div className="space-y-4 max-w-3xl">
              {studentReviews.map((fb) => (
                <Card key={fb.id} className="rounded-2xl border-border/60 shadow-sm p-5 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-base text-foreground">
                        {fb.internship_title || "Internship"}
                      </h4>
                      <p className="text-xs text-muted-foreground">{fb.company_name}</p>
                    </div>
                    <RatingDisplay value={fb.overall_rating} size="sm" showValue />
                  </div>

                  <p className="text-sm text-foreground/90 whitespace-pre-line leading-relaxed bg-muted/20 p-3 rounded-xl">
                    &ldquo;{fb.review_comments}&rdquo;
                  </p>

                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t">
                    <span>Submitted {formatDate(fb.created_at)}</span>
                    {!fb.company_response ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setRespondTarget(fb)}
                        className="rounded-lg text-xs gap-1"
                      >
                        <Reply className="size-3.5" /> Respond
                      </Button>
                    ) : (
                      <span className="text-primary font-medium">Response posted</span>
                    )}
                  </div>

                  {fb.company_response && (
                    <div className="rounded-xl border border-primary/20 bg-primary/5 p-3.5 space-y-1 text-xs">
                      <span className="font-semibold text-primary">Response:</span>
                      <p className="text-muted-foreground leading-relaxed">{fb.company_response}</p>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Tab 2: Faculty Evaluations */}
        <TabsContent value="my" className="pt-4">
          {isFacultyFbLoading ? (
            <LoadingTableSkeleton rows={3} />
          ) : facultyReviews.length === 0 ? (
            <EmptyState
              icon={Star}
              title="No institutional feedback submitted"
              description="Record evaluations of corporate partners and curriculum relevance to build long-term placement insights."
            />
          ) : (
            <div className="space-y-4 max-w-3xl">
              {facultyReviews.map((ff) => (
                <Card key={ff.id} className="rounded-2xl border-border/60 shadow-sm p-5 space-y-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-semibold text-base text-foreground">{ff.internship_title}</h4>
                      <p className="text-xs text-muted-foreground">Evaluator: {ff.faculty_name}</p>
                    </div>
                    <span className="text-xs text-muted-foreground">{formatDate(ff.created_at)}</span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-xs rounded-xl bg-muted/20 p-3">
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Cooperation</span>
                      <RatingDisplay value={ff.company_cooperation_rating} size="sm" />
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Prep Quality</span>
                      <RatingDisplay value={ff.student_preparation_rating} size="sm" />
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">Curriculum Fit</span>
                      <RatingDisplay value={ff.curriculum_relevance_rating} size="sm" />
                    </div>
                  </div>

                  <p className="text-sm text-foreground/90 leading-relaxed italic">
                    &ldquo;{ff.comments}&rdquo;
                  </p>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Respond Modal */}
      <Dialog open={!!respondTarget} onOpenChange={(o) => !o && setRespondTarget(null)}>
        <DialogContent className="max-w-md rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Respond to Student Feedback</DialogTitle>
            <DialogDescription>
              Post an official acknowledgment or follow-up to this review.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleRespond} className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="respText">Response Message</Label>
              <Textarea
                id="respText"
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                placeholder="Thank you for sharing your feedback. We have addressed..."
                rows={4}
                required
                className="rounded-xl"
              />
            </div>
            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setRespondTarget(null)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={respondToFeedback.isPending} className="rounded-xl">
                Post Response
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Institutional Feedback Modal */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg rounded-2xl p-6">
          <DialogHeader>
            <DialogTitle>Submit Institutional Program Review</DialogTitle>
            <DialogDescription>
              Record curriculum alignment and partner collaboration scores.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateFacultyFeedback} className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="intSelect">Select Internship</Label>
              <Select value={selectedInternshipId} onValueChange={setSelectedInternshipId}>
                <SelectTrigger id="intSelect" className="rounded-xl">
                  <SelectValue placeholder="Choose an internship" />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  {postings.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.title} ({p.company?.name})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3 rounded-xl border bg-muted/20 p-3.5 text-xs">
              <div className="flex justify-between items-center">
                <span>Company Cooperation</span>
                <RatingInput value={companyRating} onChange={setCompanyRating} />
              </div>
              <div className="flex justify-between items-center">
                <span>Student Preparation Quality</span>
                <RatingInput value={studentPreparationRating} onChange={setStudentPreparationRating} />
              </div>
              <div className="flex justify-between items-center">
                <span>Curriculum Relevance</span>
                <RatingInput value={curriculumRelevanceRating} onChange={setCurriculumRelevanceRating} />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="fComments">Faculty Remarks</Label>
              <Textarea
                id="fComments"
                value={facultyComments}
                onChange={(e) => setFacultyComments(e.target.value)}
                placeholder="Observed alignment, project delivery, academic feedback..."
                rows={3}
                className="rounded-xl"
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={createFacultyFb.isPending} className="rounded-xl">
                Submit Review
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
