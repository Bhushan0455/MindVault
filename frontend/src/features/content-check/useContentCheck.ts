import { useCallback, useEffect, useRef, useState } from 'react';
import { sameDraft } from '../../services/mock-content-check-service';
import type { CheckResult, ContentCheck, ContentCheckService, ContentDraft, DemoScenario } from '../../types/content-check';

export function useContentCheck(service: ContentCheckService) {
  const [scenario, setScenario] = useState<DemoScenario>('default');
  const [data, setData] = useState<ContentCheck | null>(null);
  const [draft, setDraft] = useState<ContentDraft | null>(null);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<'recheck' | 'save' | 'submit' | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [saved, setSaved] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const generation = useRef(0);
  const inFlight = useRef(false);

  useEffect(() => {
    const current = ++generation.current;
    setLoading(true); setError(''); setNotice(''); setData(null); setDraft(null); setResult(null); setSubmitted(false); setSaved(false);
    async function load() {
      try {
        const loaded = await service.load(scenario);
        const checked = loaded ? await service.recheck(loaded.draft, scenario) : null;
        if (current !== generation.current) return;
        setData(loaded); setDraft(loaded?.draft ?? null); setResult(checked);
      } catch (err) {
        if (current === generation.current) setError(err instanceof Error ? err.message : 'Could not load the demo.');
      } finally {
        if (current === generation.current) setLoading(false);
      }
    }
    void load();
    return () => { generation.current++; };
  }, [scenario, attempt, service]);

  const edit = useCallback((field: keyof ContentDraft, value: string) => {
    setDraft((previous) => previous ? { ...previous, [field]: value } : previous);
    setSubmitted(false); setSaved(false); setNotice(''); setError('');
  }, []);
  const stale = !!draft && !!result && !sameDraft(draft, result.checkedDraft);
  const canSubmit = !!draft && !!result && !stale && result.status === 'ready' && !submitted && !!draft.title.trim() && !!draft.introduction.trim() && !!draft.promotion.trim();

  const run = useCallback(async (action: 'recheck' | 'save' | 'submit') => {
    if (!draft || !result || inFlight.current || (action === 'submit' && !canSubmit)) return;
    inFlight.current = true;
    const current = generation.current;
    setBusy(action); setError(''); setNotice('');
    try {
      if (action === 'recheck') {
        const checked = await service.recheck(draft, scenario);
        if (current !== generation.current) return;
        setResult(checked);
        setNotice(checked.findings.length ? 'Demo recheck complete. One sample price conflict needs review.' : 'Demo recheck complete. No sample price conflict remains. This is not a compliance assessment.');
      } else if (action === 'save') {
        await service.save(draft, scenario);
        if (current !== generation.current) return;
        setSaved(true); setNotice('Draft saved in this demo session. Refreshing the page resets it.');
      } else {
        await service.submit(draft, result, scenario);
        if (current !== generation.current) return;
        setSubmitted(true); setNotice('Submitted to the demo approval queue. No reviewer has been contacted.');
      }
    } catch (err) {
      if (current === generation.current) setError(err instanceof Error ? err.message : 'The demo action failed. Please retry.');
    } finally { inFlight.current = false; setBusy(null); }
  }, [draft, result, canSubmit, service, scenario]);

  function quickFix() {
    if (data && draft && !busy && !submitted) {
      edit('promotion', draft.promotion.replaceAll(data.finding.original, data.finding.replacement));
      setNotice('Sample price correction applied. Recheck to update the demo findings.');
    }
  }

  return { scenario, setScenario, data, draft, result, loading, busy, error, notice, submitted, saved, stale, canSubmit, edit, run, quickFix, retry: () => setAttempt((value) => value + 1) };
}
