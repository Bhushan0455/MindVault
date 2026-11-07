import { mockContentCheck } from '../mocks/content-check';
import type { CheckResult, ContentCheckService, ContentDraft, DemoScenario } from '../types/content-check';
import { mockSessionStore, type MockSessionStore } from './mock-session-store';

const delay = () => new Promise<void>((resolve) => setTimeout(resolve, 550));
const assertAvailable = (scenario: DemoScenario) => {
  if (scenario === 'error') throw new Error('The simulated service is unavailable. Your edits are still here. Retry or switch to Default.');
};

export function sameDraft(a: ContentDraft, b: ContentDraft): boolean {
  return (Object.keys(a) as (keyof ContentDraft)[]).every((key) => a[key] === b[key]);
}

export function simulateCheck(draft: ContentDraft): CheckResult {
  // Fixture behavior only. This never evaluates real compliance or any other claims.
  const findings = draft.promotion.includes(mockContentCheck.finding.original) ? [structuredClone(mockContentCheck.finding)] : [];
  return { status: findings.length ? 'needs-review' : 'ready', findings, checkedDraft: structuredClone(draft), simulated: true };
}

export function assertSubmittable(draft: ContentDraft, result: CheckResult): void {
  if (!draft.title.trim() || !draft.introduction.trim() || !draft.promotion.trim()) throw new Error('Complete all draft fields before submitting.');
  if (!sameDraft(draft, result.checkedDraft)) throw new Error('Recheck your latest edits before submitting.');
  if (result.findings.length || result.status !== 'ready') throw new Error('Resolve the demo conflict and recheck before submitting.');
}

export function createMockContentCheckService(store: MockSessionStore = mockSessionStore): ContentCheckService {
  return {
    async load(scenario) {
      await delay();
      assertAvailable(scenario);
      if (scenario === 'empty') return null;
      const content = structuredClone(mockContentCheck);
      content.draft = store.getCreatorDraft(content.draft.id) ?? content.draft;
      return content;
    },
    async recheck(draft, scenario) {
      await delay();
      assertAvailable(scenario);
      return simulateCheck(draft);
    },
    async save(_draft, scenario) {
      await delay();
      assertAvailable(scenario);
      // Deliberately session-only: no network or implicit localStorage persistence.
    },
    async submit(draft, result, scenario) {
      await delay();
      assertAvailable(scenario);
      assertSubmittable(draft, result);
      store.recordSubmission(draft);
    },
  };
}

export const mockContentCheckService = createMockContentCheckService();
