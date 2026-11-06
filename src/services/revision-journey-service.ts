import type { ReviewerQueueService } from '../types/reviewer-queue';
import type { ReviewerDetailService } from '../types/reviewer-detail';
import type { RevisionJourneyService } from '../types/revision-journey';

// Read-only composition of existing adapters; there is no second timeline store.
export function createRevisionJourneyService(queue: ReviewerQueueService, review: ReviewerDetailService): RevisionJourneyService {
  return {
    subscribe: review.subscribe,
    async load(contentId, scenario) {
      const submissions = await queue.load(scenario === 'error' ? 'error' : 'default');
      const submission = submissions.find((item) => item.id === contentId || item.sourceDraftId === contentId || item.draft?.id === contentId);
      if (!submission) return null;
      const history = await review.load(submission.id, 'default');
      return scenario === 'empty' && history ? { ...history, events: [] } : history;
    },
  };
}
