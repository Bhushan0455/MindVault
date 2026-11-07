import type { ReviewerQueueService } from '../types/reviewer-queue';
import { mockSessionStore, type MockSessionStore } from './mock-session-store';
import { mockQueueHistory } from '../mocks/reviewer-queue';

export function createMockReviewerQueueService(store: MockSessionStore = mockSessionStore, latency = 550): ReviewerQueueService {
  return {
    subscribe: store.subscribe,
    getSnapshot: store.getSnapshot,
    getHistory: () => ({ ...mockQueueHistory }),
    async load(scenario) {
      await new Promise<void>((resolve) => setTimeout(resolve, latency));
      if (scenario === 'error') throw new Error('The simulated queue service is unavailable. Retry or switch Preview state to Default.');
      return scenario === 'empty' ? [] : structuredClone(store.getSnapshot());
    },
  };
}

export const mockReviewerQueueService = createMockReviewerQueueService();
