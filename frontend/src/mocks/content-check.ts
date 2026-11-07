import type { ContentCheck } from '../types/content-check';

export const mockProductName = 'Aura ANC True Wireless Earbuds';

export const metadataOptions = {
  channel: ['Instagram Carousel & Story', 'Instagram Feed', 'Instagram Story'],
  audience: ['Tier-1 Metro • Tech Enthusiasts', 'General Audience', 'Returning Customers'],
  region: ['India (INR - ₹)'],
  language: ['English (IN)', 'Hindi (IN)'],
};

export const mockContentCheck: ContentCheck = {
  draft: {
    id: 'CHK-9042',
    title: 'Silence the noise. Elevate your everyday rhythm.',
    introduction: 'Experience acoustic immersion with Aura ANC True Wireless Earbuds. Engineered with bespoke titanium diaphragm drivers delivering ultra-low latency spatial sound, paired with an industry-grade 40-hour hybrid battery life.',
    promotion: 'Grab yours exclusively at an introductory price of ₹799 during our pre-monsoon flash drop. Valid while stocks last. #AuraAudio #SilenceTheNoise #ANC #Launch',
    channel: 'Instagram Carousel & Story',
    audience: 'Tier-1 Metro • Tech Enthusiasts',
    region: 'India (INR - ₹)',
    language: 'English (IN)',
  },
  campaign: 'Aura Sound ANC Wireless Headphones — Festive Early Bird Ad',
  creator: 'Priyanshi Roy',
  rulebook: 'Aura Hardware v3.4',
  claims: [
    { label: '40-hour hybrid battery life', source: 'HW-SPEC-ANC-v3.1' },
    { label: 'Titanium diaphragm drivers', source: 'Acoustic Whitepaper' },
  ],
  finding: { id: 'price-conflict', ruleId: 'MAP-IN', title: 'Promotional Price Conflict', original: '₹799', replacement: '₹999' },
  source: {
    title: 'Aura Global Commercial Guidelines 2024',
    quote: 'The India promotional baseline for SKU AUR-ANC-BLK is fixed at INR 999.00 net inclusive of GST. No retailer or direct channel may advertise below this threshold.',
    location: 'Section 4.2 · Page 19',
  },
};
