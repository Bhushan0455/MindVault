import { useEffect, useState } from 'react';
import type { DemoScenario } from '../../types/content-check';
import type { SubmissionReview } from '../../types/reviewer-detail';
import type { RevisionJourneyService } from '../../types/revision-journey';

export function useRevisionJourney(contentId: string, service: RevisionJourneyService) {
  const [data, setData] = useState<SubmissionReview | null>(null);
  const [scenario, setScenario] = useState<DemoScenario>('default');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => service.subscribe(() => setAttempt((value) => value + 1)), [service]);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    void service.load(contentId, scenario).then((loaded) => { if (active) setData(loaded); }).catch((reason: unknown) => { if (active) { setData(null); setError(reason instanceof Error ? reason.message : 'Could not load revision history.'); } }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [contentId, service, scenario, attempt]);
  return { data, scenario, setScenario, loading, error, retry: () => setAttempt((value) => value + 1) };
}
