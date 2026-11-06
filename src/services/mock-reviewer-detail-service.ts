import type { ReviewerDetailService } from '../types/reviewer-detail';
import { mockSessionStore, type MockSessionStore } from './mock-session-store';

export function createMockReviewerDetailService(store: MockSessionStore = mockSessionStore, latency = 450): ReviewerDetailService {
  const delay = () => new Promise<void>((resolve) => setTimeout(resolve, latency));
  return {
    subscribe: store.subscribe,
    async load(submissionId, scenario) {
      await delay();
      if (scenario === 'error') throw new Error('The simulated review service is unavailable. Retry or switch Preview state to Default.');
      return scenario === 'empty' ? null : store.getReview(submissionId);
    },
    async decide(request, scenario) {
      const captured = structuredClone(request);
      await delay();
      if (scenario === 'error') throw new Error('The simulated decision could not be saved. Your reviewer comment is still available.');
      return store.decide(captured);
    },
  };
}

export const mockReviewerDetailService = createMockReviewerDetailService();
