import { mockContentCheck } from './content-check';
import { mockWorkspace } from './app-shell';
import type { ContentDraft } from '../types/content-check';
import type { ReviewAsset, ReviewFinding } from '../types/reviewer-detail';
import type { QueueSubmission } from '../types/reviewer-queue';

export const mockReviewerName = `${mockWorkspace.user.name} (Demo Reviewer)`;

export const mockReviewAssets = [
  { name: 'Aura_ANC_KeyArt_1080x1080.png', label: 'Key Art · 1080×1080', description: 'Reference creative · File not supplied locally' },
  { name: 'Aura_PriceDrop_Card.png', label: 'Promotional creative', description: 'Reference creative · File not supplied locally' },
] as const;

export function reviewAssetsFor(item: QueueSubmission): readonly ReviewAsset[] {
  return item.sourceDraftId === mockContentCheck.draft.id ? structuredClone(mockReviewAssets) : [];
}

// These fictional copy fixtures fill records whose queue export supplied titles only.
// Once seeded, the store keeps their exact text as a submitted revision snapshot.
export function seedReviewDraft(item: QueueSubmission): ContentDraft {
  if (item.draft) return structuredClone(item.draft);
  return {
    id: item.sourceDraftId ?? item.id,
    title: item.title,
    introduction: `Discover the latest from ${item.brand}. Explore ${item.campaign.toLowerCase()} with thoughtfully designed products for your everyday routine.`,
    promotion: `Find your next favorite with ${item.brand}. Explore the collection and discover more. #${item.brand.replaceAll(' ', '')}`,
    channel: item.channel, region: item.region,
    audience: 'Brand community · Demo audience', language: 'English (EN)',
  };
}

export function createReviewFindings(item: QueueSubmission, draft: ContentDraft): ReviewFinding[] {
  if (item.brand === 'Aura Audio' && draft.introduction.includes('Aura ANC True Wireless Earbuds')) {
    const price = draft.promotion.includes('₹799') ? '₹799' : draft.promotion.includes('₹999') ? '₹999' : '';
    return [
      { id: 'price', ruleId: mockContentCheck.finding.ruleId, title: 'Promotional price baseline', claim: price, status: price === '₹999' ? 'matched' : price === '₹799' ? 'attention' : 'advisory', severity: price === '₹799' ? 'blocker' : price === '₹999' ? 'none' : 'advisory', explanation: price === '₹799' ? 'The submitted ₹799 price conflicts with the sample ₹999 baseline. Request a corrected revision before approval.' : price === '₹999' ? 'The submitted text contains the ₹999 sample baseline. This is a fixture string match, not a regulatory assessment.' : 'The fixture price was not found. A reviewer should inspect the submitted pricing language.', sources: [structuredClone(mockContentCheck.source)], simulated: true },
      ...mockContentCheck.claims.map((claim, index): ReviewFinding => {
        const present = draft.introduction.toLowerCase().includes(claim.label.toLowerCase());
        return { id: `hardware-${index}`, ruleId: index === 0 ? 'SPEC-BATTERY-04' : 'SPEC-AUDIO-04', title: claim.label, claim: present ? claim.label : '', status: present ? 'matched' : 'advisory', severity: present ? 'none' : 'advisory', explanation: present ? 'The claim text is associated with a sample source in this demo. No technical testing or real AI analysis has been performed.' : 'The original sample claim is absent from this revision. Inspect the changed copy before deciding.', sources: [{ title: claim.source, quote: `Sample reference text: ${claim.label}.`, location: 'Demo brand knowledge excerpt · Original document not supplied' }], simulated: true };
      }),
    ];
  }
  return [{ id: 'brand-rule', ruleId: 'BRAND-REVIEW-01', title: `${item.brand} editorial review`, claim: '', severity: item.severity, status: item.severity === 'none' ? 'matched' : item.severity === 'advisory' ? 'advisory' : 'attention', explanation: item.summary, sources: [{ title: `${item.brand} sample brand guidelines`, quote: 'Use approved brand terminology and include the disclosures relevant to the intended channel. This is fictional demo guidance.', location: 'Demo excerpt · No original source document provided' }], simulated: true }];
}
