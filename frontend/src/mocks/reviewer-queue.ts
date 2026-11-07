import { mockContentCheck } from './content-check';
import type { QueueHistory, QueueSubmission } from '../types/reviewer-queue';

export const mockQueueHistory: QueueHistory = { reviewedBeforeVisibleQueue: 73, approvedYesterday: 10 };

export function createMockSubmissions(now = Date.now()): QueueSubmission[] {
  const minute = 60_000;
  const day = 24 * 60 * minute;
  const base = { brand: 'Aura Audio', origin: 'stitch-fixture', simulated: true } as const;
  const approved = { status: 'approved', severity: 'none', statusLabel: 'Approved', summary: 'Sample claim checks complete; mock reviewer sign-off recorded.', approvedAt: now } as const;
  const records: QueueSubmission[] = [
    { ...base, id: 'REV-2024-884', sourceDraftId: mockContentCheck.draft.id, title: 'Wireless Headphones Launch — Instagram Feed Post', campaign: 'Aura Sound ANC Launch', assetDescription: '3 Assets', submittedBy: { name: mockContentCheck.creator, team: 'Growth Mktg', initials: 'PR' }, channel: 'Instagram Carousel & Story', region: 'India (INR)', submittedAt: now - 12 * minute, status: 'pending', severity: 'blocker', statusLabel: 'Needs Review (1 Blocker)', summary: 'MAP Conflict: ₹799 vs ₹999 sample baseline', draft: structuredClone(mockContentCheck.draft) },
    { ...base, id: 'REV-2024-885', title: 'Monsoon Soundfest Influencer Brief & Reel Script', campaign: 'Creator Partner Series', assetDescription: 'Script v2', submittedBy: { name: 'Alex Chen', team: 'Social & Influencer', initials: 'AC' }, channel: 'TikTok & Reels', region: 'India (INR)', submittedAt: now - 45 * minute, status: 'pending', severity: 'warning', statusLabel: 'Needs Review (2 Warnings)', summary: 'Sample ASCI disclosure tag missing on reel end-frame.' },
    { ...base, id: 'REV-2024-879', title: 'Winter Sale Email — Tier-1 Flash Drop Newsletter', campaign: 'Segment: High LTV Buyers', assetDescription: 'HTML Email', submittedBy: { name: 'Priyanshi Roy', team: 'CRM Marketing', initials: 'PR' }, channel: 'Email Campaign', region: 'Global (EN)', submittedAt: now - 120 * minute, status: 'changes-requested', severity: 'warning', statusLabel: 'Changes Requested', summary: 'Sample reviewer feedback: add the unsubscribe disclaimer and ASCI footnote.' },
    { ...base, ...approved, id: 'REV-2024-872', title: 'Product Announcement — Titanium Diaphragm Press Release', campaign: 'Editorial Wire', assetDescription: 'Wire syndication', brand: 'Solace Home', submittedBy: { name: 'Jane Doe', team: 'Communications', initials: 'JD' }, channel: 'PR / Press Wire', region: 'US / CA', submittedAt: now - day },
    { ...base, ...approved, id: 'REV-2024-869', title: 'Q3 Loyalty Rewards Retargeting Banner Set', campaign: 'Display Retargeting 300×250', assetDescription: '8 Creatives', brand: 'Lumina Skincare', submittedBy: { name: 'Maya Patel', team: 'Performance Mktg', initials: 'MP' }, channel: 'Google Display', region: 'Tier 1 Markets', submittedAt: now - 2 * day },
    { ...base, id: 'REV-2024-867', title: 'Aura Studio Listening Party — Event Invitation', campaign: 'Studio Sessions', assetDescription: '2 Creatives', submittedBy: { name: 'Rohan Mehta', team: 'Growth Mktg', initials: 'RM' }, channel: 'Email Campaign', region: 'India (INR)', submittedAt: now - 3 * day, status: 'pending', severity: 'advisory', statusLabel: 'Pending Review (1 Advisory)', summary: 'Sample advisory: confirm the event date before publishing.' },
    { ...base, id: 'REV-2024-866', title: 'Solace Home Warranty Landing Page Copy', campaign: 'Care Beyond Purchase', assetDescription: 'Web copy', brand: 'Solace Home', submittedBy: { name: 'Jane Doe', team: 'Communications', initials: 'JD' }, channel: 'Website', region: 'US / CA', submittedAt: now - 4 * day, status: 'changes-requested', severity: 'advisory', statusLabel: 'Changes Requested', summary: 'Sample reviewer feedback: clarify the warranty eligibility statement.' },
  ];
  const archive = [
    ['Aura ANC Product Comparison', 'Aura Audio', 'Website'],
    ['Lumina Daily SPF — Summer Campaign', 'Lumina Skincare', 'Instagram Feed'],
    ['Solace Smart Lamp Launch', 'Solace Home', 'Google Display'],
    ['Aura Weekend Listening Newsletter', 'Aura Audio', 'Email Campaign'],
    ['Lumina Hydration Routine Carousel', 'Lumina Skincare', 'Instagram Carousel & Story'],
    ['Solace Home Creator Welcome Kit', 'Solace Home', 'TikTok & Reels'],
    ['Aura Studio Headphones Press Note', 'Aura Audio', 'PR / Press Wire'],
    ['Lumina Loyalty Member Email', 'Lumina Skincare', 'Email Campaign'],
    ['Solace Reading Corner Promotion', 'Solace Home', 'Instagram Feed'],
    ['Aura Festival Sound Guide', 'Aura Audio', 'Website'],
    ['Lumina Product Care Cards', 'Lumina Skincare', 'Google Display'],
    ['Solace Seasonal Brand Announcement', 'Solace Home', 'PR / Press Wire'],
  ];
  archive.forEach(([title, brand, channel], index) => records.push({ ...base, ...approved, id: `REV-2024-${860 - index}`, title, campaign: 'Brand campaign archive', assetDescription: 'Approved sample asset', brand, channel, region: index % 2 ? 'Global (EN)' : 'India (INR)', submittedBy: index % 2 ? { name: 'Maya Patel', team: 'Performance Mktg', initials: 'MP' } : { name: 'Alex Chen', team: 'Social & Influencer', initials: 'AC' }, submittedAt: now - (5 + index) * day }));
  records[0].contentCheckPath = '/content-checks';
  return records;
}
