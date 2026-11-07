import { useMemo } from 'react';
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { ApplicationShell, navigation } from './components/ApplicationShell';
import { ErrorBoundary, StatePanel } from './components/ui';
import { ContentCheckPage } from './features/content-check/ContentCheckPage';
import { mockContentCheckService } from './services/mock-content-check-service';
import { mockReviewerQueueService } from './services/mock-reviewer-queue-service';
import { ReviewerQueuePage } from './features/reviewer-queue/ReviewerQueuePage';
import type { ContentCheckService } from './types/content-check';
import type { ReviewerQueueService } from './types/reviewer-queue';
import type { ReviewerDetailService } from './types/reviewer-detail';
import { mockReviewerDetailService } from './services/mock-reviewer-detail-service';
import { ReviewerDetailPage } from './features/reviewer-detail/ReviewerDetailPage';
import { RevisionJourneyPage } from './features/revision-journey/RevisionJourneyPage';
import { createRevisionJourneyService } from './services/revision-journey-service';
import type { RevisionJourneyService } from './types/revision-journey';

function PendingScreen() {
  const { pathname } = useLocation();
  const label = navigation.flatMap((group) => group.items).find((item) => item.path === pathname)?.label;
  return <StatePanel title={label ? `${label} is coming in a later step` : 'Page not found'}><p>This implementation includes Content Checks and the Reviewer Queue.</p><Link className="button button-primary" to="/content-checks">Go to Content Checks</Link></StatePanel>;
}

export function App({ contentService = mockContentCheckService, queueService = mockReviewerQueueService, reviewService = mockReviewerDetailService, journeyService }: { contentService?: ContentCheckService; queueService?: ReviewerQueueService; reviewService?: ReviewerDetailService; journeyService?: RevisionJourneyService }) {
  const history = useMemo(() => journeyService ?? createRevisionJourneyService(queueService, reviewService), [journeyService, queueService, reviewService]);
  return <ErrorBoundary><Routes><Route element={<ApplicationShell queueService={queueService} />}><Route index element={<Navigate to="/content-checks" replace />} /><Route path="content-checks" element={<ContentCheckPage service={contentService} />} /><Route path="approvals" element={<ReviewerQueuePage service={queueService} />} /><Route path="approvals/:submissionId" element={<ReviewerDetailPage service={reviewService} />} /><Route path="content/:contentId/history" element={<RevisionJourneyPage service={history} />} /><Route path="*" element={<PendingScreen />} /></Route></Routes></ErrorBoundary>;
}
