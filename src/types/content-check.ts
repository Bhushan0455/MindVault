export type DemoScenario = 'default' | 'empty' | 'error';
export type ReviewStatus = 'needs-review' | 'ready' | 'submitted';

export interface ContentDraft {
  id: string;
  title: string;
  introduction: string;
  promotion: string;
  channel: string;
  audience: string;
  region: string;
  language: string;
}

export interface Finding {
  id: string;
  ruleId: string;
  title: string;
  original: string;
  replacement: string;
}

export interface VerifiedClaim {
  label: string;
  source: string;
}

export interface RuleSource {
  title: string;
  quote: string;
  location: string;
}

export interface ContentCheck {
  draft: ContentDraft;
  campaign: string;
  creator: string;
  rulebook: string;
  claims: VerifiedClaim[];
  finding: Finding;
  source: RuleSource;
}

export interface CheckResult {
  status: Exclude<ReviewStatus, 'submitted'>;
  findings: Finding[];
  checkedDraft: ContentDraft;
  simulated: true;
}

// The UI depends on this contract; a teammate can supply an API adapter later.
export interface ContentCheckService {
  load(scenario: DemoScenario): Promise<ContentCheck | null>;
  recheck(draft: ContentDraft, scenario: DemoScenario): Promise<CheckResult>;
  save(draft: ContentDraft, scenario: DemoScenario): Promise<void>;
  submit(draft: ContentDraft, result: CheckResult, scenario: DemoScenario): Promise<void>;
}
