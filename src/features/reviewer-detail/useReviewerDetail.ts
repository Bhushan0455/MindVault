import { useEffect, useRef, useState } from 'react';
import type { DemoScenario } from '../../types/content-check';
import type { ReviewDecisionRequest, ReviewerDetailService, SubmissionReview } from '../../types/reviewer-detail';

export function useReviewerDetail(submissionId: string, service: ReviewerDetailService) {
  const [data, setData] = useState<SubmissionReview | null>(null);
  const [scenario, setScenario] = useState<DemoScenario>('default');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [attempt, setAttempt] = useState(0);
  const operation = useRef(false);
  const generation = useRef(0);

  useEffect(() => service.subscribe(() => { if (!operation.current) setAttempt((value) => value + 1); }), [service]);
  useEffect(() => {
    const current = ++generation.current;
    setLoading(true); setError(''); setNotice('');
    void service.load(submissionId, scenario).then((loaded) => { if (generation.current === current) setData(loaded); }).catch((reason: unknown) => {
      if (generation.current === current) { setData(null); setError(reason instanceof Error ? reason.message : 'Could not load the submitted revision.'); }
    }).finally(() => { if (generation.current === current) setLoading(false); });
    return () => { generation.current++; };
  }, [submissionId, service, scenario, attempt]);

  async function decide(request: ReviewDecisionRequest) {
    if (operation.current) return false;
    operation.current = true;
    const current = generation.current;
    setBusy(true); setError(''); setNotice('');
    try {
      const updated = await service.decide(request, scenario);
      if (current !== generation.current) return false;
      setData(updated);
      setNotice(request.kind === 'approved' ? 'Revision approved in this demo session. The queue status has been updated.' : 'Changes requested. Your comment is saved with this revision and visible in the queue.');
      return true;
    } catch (reason) {
      if (current === generation.current) setError(reason instanceof Error ? reason.message : 'Could not save the demo review decision.');
      return false;
    } finally {
      operation.current = false;
      if (current === generation.current) setBusy(false);
    }
  }

  return { data, scenario, setScenario, loading, busy, error, notice, decide, retry: () => setAttempt((value) => value + 1) };
}
