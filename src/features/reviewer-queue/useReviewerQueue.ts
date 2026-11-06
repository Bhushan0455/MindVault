import { useEffect, useState } from 'react';
import type { DemoScenario } from '../../types/content-check';
import type { QueueSubmission, ReviewerQueueService } from '../../types/reviewer-queue';

export function useReviewerQueue(service: ReviewerQueueService) {
  const [scenario, setScenario] = useState<DemoScenario>('default');
  const [records, setRecords] = useState<readonly QueueSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => service.subscribe(() => setAttempt((value) => value + 1)), [service]);
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError('');
    void service.load(scenario).then((items) => {
      if (!cancelled) setRecords(items);
    }).catch((reason: unknown) => {
      if (!cancelled) { setRecords([]); setError(reason instanceof Error ? reason.message : 'Could not load the demo queue.'); }
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [service, scenario, attempt]);

  return { scenario, setScenario, records, loading, error, retry: () => setAttempt((value) => value + 1) };
}
