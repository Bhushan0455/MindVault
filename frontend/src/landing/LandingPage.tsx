import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronDown,
  FileCheck2,
  FileText,
  Menu,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import './landing.css';

const findings = [
  { severity: 'critical', label: 'CRITICAL · PRICE MISMATCH', quote: '₹799', body: 'Approved price is ₹999 for Veyra Beat 200.', source: 'PRODUCT FACT SHEET · P. 2', fix: '₹999' },
  { severity: 'high', label: 'HIGH · CLAIM NOT SUBSTANTIATED', quote: 'Best headphones in India', body: 'This claim has no supporting evidence in approved sources.', source: 'CLAIM-01 · APPROVED RULE', fix: 'Remove this claim' },
  { severity: 'high', label: 'HIGH · REQUIRED TEXT MISSING', quote: 'T&C apply', body: 'Paid ads must include the required disclaimer.', source: 'DISC-01 · APPROVED RULE', fix: 'Add “T&C apply”' },
];

const faqs = [
  ['Does AI make the final decision?', 'No. AI suggests and explains. Creators and reviewers accept, edit, reject and approve.'],
  ['What if AI gets something wrong?', 'Findings that quote text missing from your draft or cite a rule that does not exist are discarded. Low confidence findings are marked “needs review”.'],
  ['Do we have to move our documents?', 'No. Upload the guidelines and fact sheets you already have and start checking.'],
  ['What if the AI service is unavailable?', 'Rule based checks still run. The app clearly says when AI analysis is unavailable.'],
  ['Can a creator submit with critical issues open?', 'No. Submission is blocked until the current revision has no open critical or high findings.'],
  ['Is this using real company data?', 'No. The demo uses fictional Veyra Audio data only.'],
];

function Label({ children }: { children: React.ReactNode }) {
  return <span className="mono label">{children}</span>;
}

function ProductMock() {
  return (
    <div className="browser-window" aria-label="Illustration of the MindVault content review workspace">
      <div className="browser-bar">
        <span className="browser-dots"><i /><i /><i /></span>
        <span className="browser-url">app.mindvault.ai / review / veyra-beat-200</span>
        <span className="browser-avatar">MV</span>
      </div>
      <div className="product-top">
        <div className="product-brand"><span className="brand-mark small-mark">m</span><span>Veyra Audio</span><ChevronDown size={13} /></div>
        <div className="product-top-right"><span className="status-dot" /> <span>All changes saved</span><span className="reviewer-avatar">AR</span></div>
      </div>
      <div className="product-title">
        <div><Label>CONTENT REVIEW <span className="muted">/ REVISION 01</span></Label><h3>Veyra Beat 200 · Paid ad</h3></div>
        <span className="state-pill"><span className="state-dot" /> In progress</span>
      </div>
      <div className="product-grid">
        <div className="draft-pane">
          <div className="pane-head"><span><FileText size={13} /> DRAFT</span><span className="mono muted">INSTAGRAM · IN</span></div>
          <div className="draft-copy">Meet the <b>Veyra Beat 200</b>.<br /><br />Now at <mark className="red-mark">₹799</mark>! <mark className="orange-mark">Best headphones in India</mark>.<br /><br />🎧 Sound all day. 🎶</div>
          <div className="draft-foot"><span>48 words</span><span>Draft by Sam</span></div>
        </div>
        <div className="findings-pane">
          <div className="pane-head"><span><ShieldCheck size={13} /> FINDINGS</span><span className="issue-count">3 OPEN</span></div>
          {findings.map((f, i) => (
            <div className={`finding-mini ${f.severity}`} key={i}>
              <div className="finding-mini-label"><span className="severity-pin" />{f.label}</div>
              <strong>“{f.quote}”</strong>
              <p>{f.body}</p>
              <span className="mono source-mini"><FileCheck2 size={11} />{f.source}</span>
            </div>
          ))}
          <div className="product-actions"><span>Decide on each finding</span><button type="button">Review findings <ArrowRight size={12} /></button></div>
        </div>
        <div className="evidence-pane">
          <div className="pane-head"><span><FileCheck2 size={13} /> EVIDENCE</span><span className="mono muted">FINDING 01 / 03</span></div>
          <Label>APPROVED FACT · PRICE</Label>
          <div className="evidence-value">₹999 <span>INR</span></div>
          <div className="evidence-meta">
            <FileText size={14} />
            <div><strong>Veyra_Product_Facts.docx</strong><span>Page 2 · Veyra Beat 200</span></div>
          </div>
          <blockquote>“The retail price for Veyra Beat 200 in India is ₹999.”</blockquote>
          <div className="suggestion">
            <Label>SUGGESTED FIX</Label>
            <div><del>₹799</del><ArrowRight size={13} /><strong>₹999</strong></div>
          </div>
          <button type="button" className="accept-button"><Check size={13} /> Accept suggested fix</button>
          <button type="button" className="edit-button">Edit manually</button>
        </div>
      </div>
      <div className="product-bottom">
        <span><span className="green-dot" /> Rule based checks complete</span>
        <span>AI analysis complete</span>
        <span className="mono">HUMAN REVIEW REQUIRED</span>
      </div>
    </div>
  );
}

function Demo() {
  const [active, setActive] = useState(false);
  const [clean, setClean] = useState(false);
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setActive(true);
        observer.disconnect();
      }
    }, { threshold: 0.28 });
    const el = document.getElementById('demo-board');
    if (el) observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section className="section demo-section" id="demo">
      <div className="container">
        <div className="section-head">
          <div><Label>02 / THE CHECK</Label><h2>A real draft.<br />Three real problems.</h2></div>
          <p>Every finding comes with a reason, a source and a suggested next step. The decision stays with your team.</p>
        </div>
        <div className={`demo-board ${active ? 'demo-active' : ''} ${clean ? 'demo-clean' : ''}`} id="demo-board">
          <div className="demo-draft">
            <div className="demo-draft-head"><span className="demo-brand"><span className="brand-mark small-mark">m</span> VEYRA AUDIO</span><span className="mono muted">PAID SOCIAL · IN</span></div>
            <Label>CAMPAIGN DRAFT / REVISION 01</Label>
            <p className="big-draft">Veyra Beat 200 headphones now at <span className="underline-price">₹799</span>! <span className="underline-claim">Best headphones in India.</span></p>
            <span className="draft-placeholder">Add your approved disclaimer…</span>
            <div className="demo-draft-foot"><span>Draft by Sam Rivera</span><span className="mono">28 WORDS</span></div>
          </div>
          <div className="demo-results">
            <div className="demo-result-head"><Label>CHECK RESULTS</Label><span className={clean ? 'clean-tag' : 'open-tag'}>{clean ? <><Check size={12} /> 0 OPEN ISSUES</> : '3 FINDINGS'}</span></div>
            {!clean ? findings.map((f, i) => (
              <motion.article
                className={`result-card ${f.severity}`}
                key={f.label}
                initial={{ opacity: 0, x: 18 }}
                animate={{ opacity: active ? 1 : 0, x: active ? 0 : 18 }}
                transition={{ delay: 0.35 + i * 0.4, duration: 0.45 }}
              >
                <div className="result-card-top"><span className="severity-pill"><span className="severity-pin" />{f.severity}</span><Label>{i === 0 ? 'CLAIMS' : i === 1 ? 'CLAIMS' : 'DISCLAIMER'}</Label></div>
                <strong>{f.quote}</strong>
                <p>{f.body}</p>
                <span className="mono result-source"><FileCheck2 size={12} />{f.source}</span>
              </motion.article>
            )) : (
              <div className="clean-result">
                <div className="clean-icon"><CheckCheck size={20} /></div>
                <div>
                  <strong>Looks clear to publish.</strong>
                  <p>The current revision has no open critical or high findings. Submit it for reviewer sign off.</p>
                  <Label>REVISION 02 · RE-CHECK COMPLETE</Label>
                </div>
              </div>
            )}
            <div className="demo-result-foot">
              {clean ? <span><CheckCheck size={13} /> Accepted fixes · re-checked automatically</span> : <span><Sparkles size={13} /> Demo findings are illustrative</span>}
              <button type="button" onClick={() => { setClean(!clean); setActive(true); }}>{clean ? 'View findings' : <>Accept fixes <ArrowRight size={13} /></>}</button>
            </div>
          </div>
        </div>
        <p className="demo-caption"><span className="green-dot" /> A creator applies fixes. The new revision is checked again before it goes to a reviewer.</p>
      </div>
    </section>
  );
}

function FeatureVisual({ kind }: { kind: number }) {
  return (
    <div className={`feature-visual visual-${kind}`}>
      {kind === 1 && (
        <>
          <div className="visual-document">
            <div className="doc-ribbon"><FileText size={13} /> Brand_Guidelines_2026.pdf <span>PAGE 04</span></div>
            <div className="doc-lines"><b>Claims &amp; product language</b><i /><i /><i className="short" /><b>Pricing and promotions</b><i /><i className="short" /></div>
          </div>
          <div className="extract-card">
            <Label>EXTRACTED RULE · 04</Label>
            <strong>Price claims must match the current approved product fact.</strong>
            <div className="extract-source"><FileCheck2 size={13} /> Source · Page 4</div>
            <div className="extract-actions"><button type="button">Approve</button><button type="button">Edit</button><button type="button">Reject</button></div>
          </div>
        </>
      )}
      {kind === 2 && (
        <>
          <div className="context-top"><span className="mini-brand"><span className="brand-mark small-mark">m</span> RULE CONTEXT</span><span className="context-tag">INSTAGRAM / IN</span></div>
          <p className="context-quote">“Use a conversational tone and no more than two emojis.”</p>
          <div className="context-divider" />
          <Label>APPLIED TO THIS DRAFT</Label>
          <div className="context-rule"><Check size={13} /> TONE-IG-02 <span>matches channel</span></div>
          <div className="context-rule skipped"><ArrowRight size={13} /> TONE-INV-03 <span>skipped · not an investor deck</span></div>
          <div className="context-footer">Rule scope explained for every check <ArrowUpRight size={13} /></div>
        </>
      )}
      {kind === 3 && (
        <>
          <div className="audit-head"><span><Sparkles size={13} /> GUIDELINE CLARITY AUDITOR</span><span className="audit-count">2 NEED CLARITY</span></div>
          <div className="audit-rule"><Label>ORIGINAL RULE · VAGUE</Label><p>“Headlines should be short.”</p></div>
          <div className="audit-rule proposed"><Label>PROPOSED WORDING</Label><p>“Keep paid social headlines under 40 characters, including spaces.”</p><span><Check size={12} /> Includes a measurable limit</span></div>
          <div className="audit-approve">Review suggestion <ArrowRight size={13} /></div>
        </>
      )}
    </div>
  );
}

export function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const reduceMotion = useReducedMotion();

  return (
    <div className="landing-root">
      <div className="announcement">
        <span>INTRODUCING</span>
        <i /> Guideline Clarity Auditor finds vague rules and proposes clearer wording <ArrowRight size={13} />
      </div>

      <header className="nav">
        <div className="nav-inner container">
          <a href="#top" className="wordmark">
            <span className="brand-mark">m</span>
            <span>MINDVAULT<span className="wordmark-ai"> AI</span></span>
          </a>

          <nav className={menuOpen ? 'nav-links nav-open' : 'nav-links'}>
            <a href="#product" onClick={() => setMenuOpen(false)}>PRODUCT</a>
            <a href="#how" onClick={() => setMenuOpen(false)}>HOW IT WORKS</a>
            <a href="#roles" onClick={() => setMenuOpen(false)}>ROLES</a>
            <a href="#faq" onClick={() => setMenuOpen(false)}>FAQ</a>
          </nav>

          <div className="nav-actions">
            <Link to="/dashboard" className="button">
              Open Workspace <ArrowUpRight size={14} />
            </Link>
          </div>

          <button
            type="button"
            className="menu-toggle"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          >
            {menuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <div className="container">
            <div className="hero-copy">
              <motion.div
                initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="hero-eyebrow"
              >
                <span className="eyebrow-line" /> <Label>BRAND GOVERNANCE BEFORE YOU PUBLISH</Label>
              </motion.div>

              <motion.h1
                initial={reduceMotion ? false : { opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.08 }}
              >
                Make every draft<br className="desktop-break" /> ready for <span className="hero-underline">the world.</span>
              </motion.h1>

              <motion.p
                className="hero-sub"
                initial={reduceMotion ? false : { opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.65, delay: 0.2 }}
              >
                MindVault AI checks every draft against your approved rules and facts, shows the proof for each problem, and lets a human make the final call.
              </motion.p>

              <motion.div
                className="hero-actions"
                initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.3 }}
              >
                <a href="#how" className="walkthrough-link">
                  <span className="play-icon">▶</span> See how it works <ArrowDown size={13} />
                </a>
              </motion.div>

              <motion.div
                className="hero-trust mono"
                initial={reduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5, duration: 0.5 }}
              >
                <span>HUMAN APPROVES EVERYTHING</span><i />
                <span>EVERY FINDING CITES ITS SOURCE</span><i />
                <span>NO MIGRATION NEEDED</span>
              </motion.div>
            </div>

            <div className="hero-product" id="product">
              <div className="hero-product-label mono">
                <span>THE REVIEW WORKSPACE</span><span>01 — 03</span>
              </div>
              <motion.div
                className="product-perspective"
                initial={reduceMotion ? false : { rotateX: 16, rotateY: -8, scale: 0.96, opacity: 0 }}
                whileInView={{ rotateX: 0, rotateY: 0, scale: 1, opacity: 1 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 1.15, ease: [0.22, 1, 0.36, 1] }}
              >
                <ProductMock />
              </motion.div>
              <div className="hero-note mono">
                <span>01</span> A CLEAR TRAIL FROM DRAFT TO DECISION <ArrowDown size={12} />
              </div>
            </div>
          </div>
        </section>

        <section className="problem-strip">
          <div className="container problem-inner">
            <Label>WHAT GOES<br />WRONG TODAY</Label>
            <span>A price that doesn’t match the fact sheet</span>
            <span>A boast nobody can prove</span>
            <span>The wrong tone for the channel</span>
            <span>A missing “T&amp;C apply”</span>
          </div>
        </section>

        <section className="numbers">
          <div className="container number-grid">
            {[
              ['03', 'ROLES IN THE REVIEW LOOP'],
              ['05', 'CHECKING STEPS PER DRAFT'],
              ['100%', 'FINDINGS CARRY EVIDENCE'],
              ['0', 'RULES TRUSTED WITHOUT APPROVAL'],
            ].map(([n, label], i) => (
              <div className="number-cell" key={label}>
                <motion.div
                  className="number"
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.5 }}
                  transition={{ delay: i * 0.08, duration: 0.5 }}
                >
                  {n}
                </motion.div>
                <Label>{label}</Label>
              </div>
            ))}
          </div>
        </section>

        <Demo />

        <section className="section features-section">
          <div className="container">
            <div className="section-head feature-head">
              <div><Label>03 / BUILT FOR REAL WORK</Label><h2>Govern the knowledge.<br />Keep work moving.</h2></div>
              <p>Bring the brand knowledge you already have. Give each team the context and evidence to make a good call.</p>
            </div>
            <div className="feature-row">
              <div className="feature-text">
                <Label>01 / ZERO-MIGRATION START</Label>
                <h3>Start with the documents you have.</h3>
                <p>Upload a guideline and fact sheet. MindVault proposes rules and facts with their source, then your team approves what becomes trusted.</p>
                <a href="#how" className="text-link">Explore the workflow <ArrowRight size={14} /></a>
              </div>
              <FeatureVisual kind={1} />
            </div>
            <div className="feature-row reverse">
              <div className="feature-text">
                <Label>02 / CONTEXT-AWARE BRAND BRAIN</Label>
                <h3>Rules that know where the work goes.</h3>
                <p>The same sentence can be right on Instagram and wrong in an investor deck. Checks use the channel, region and audience, and explain what applied or was skipped.</p>
                <a href="#how" className="text-link">See how checks work <ArrowRight size={14} /></a>
              </div>
              <FeatureVisual kind={2} />
            </div>
            <div className="feature-row">
              <div className="feature-text">
                <Label>03 / GUIDELINE CLARITY AUDITOR</Label>
                <h3>Turn “it depends” into a clear rule.</h3>
                <p>Find vague guidance before it creates inconsistent reviews. MindVault proposes measurable wording and examples for a person to review.</p>
                <a href="#how" className="text-link">See the clarity audit <ArrowRight size={14} /></a>
              </div>
              <FeatureVisual kind={3} />
            </div>
          </div>
        </section>

        <section className="section how-section" id="how">
          <div className="container">
            <div className="section-head">
              <div><Label>04 / HOW IT WORKS</Label><h2>Five steps. One clear decision.</h2></div>
              <p>From source document to reviewer sign off, every step leaves a record your team can follow.</p>
            </div>
            <div className="steps-grid">
              {[
                ['01', 'Upload your guidelines', 'PDF or DOCX. The exact sentence and page stay attached.'],
                ['02', 'Approve rules and facts', 'Nothing is trusted until a person approves it.'],
                ['03', 'Paste a draft and check', 'Rule based checks first, then AI for tone and meaning.'],
                ['04', 'Fix with evidence', 'Accept, edit or reject each finding. Rejections need a reason.'],
                ['05', 'Reviewer signs off', 'Approval belongs to the exact revision in the history.'],
              ].map(([n, title, body], i) => (
                <article className="step" key={n}>
                  <span className="step-no mono">{n}</span>
                  {i < 4 && <span className="step-connector" />}
                  <h3>{title}</h3>
                  <p>{body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section roles-section" id="roles">
          <div className="container">
            <div className="section-head">
              <div><Label>05 / YOUR TEAM</Label><h2>Built for the three people in the loop.</h2></div>
              <p>Clear ownership helps good work move from source material to approved content.</p>
            </div>
            <div className="roles-grid">
              <article className="role-card">
                <Label>01 / ADMIN</Label>
                <div className="role-icon"><ShieldCheck size={18} /></div>
                <h3>Govern the source.</h3>
                <p>Uploads source documents, approves rules and facts, and runs the clarity audit.</p>
                <span className="role-footer">KNOWLEDGE · RULES · FACTS</span>
              </article>
              <article className="role-card creator-role">
                <div className="creator-tag mono">WHERE MOST WORK HAPPENS</div>
                <Label>02 / CREATOR</Label>
                <div className="role-icon"><FileText size={18} /></div>
                <h3>Make the draft ready.</h3>
                <p>Checks content, resolves findings, applies fixes and submits a clean revision for review.</p>
                <span className="role-footer">DRAFT · DECIDE · SUBMIT</span>
              </article>
              <article className="role-card">
                <Label>03 / REVIEWER</Label>
                <div className="role-icon"><CheckCheck size={18} /></div>
                <h3>Approve with confidence.</h3>
                <p>Reads the exact revision and approves it or requests changes. Changed text means a new review.</p>
                <span className="role-footer">QUEUE · VERIFY · APPROVE</span>
              </article>
            </div>
          </div>
        </section>

        <section className="trust-section" id="trust">
          <div className="container trust-inner">
            <div className="trust-heading">
              <Label>06 / TRUST &amp; SAFETY</Label>
              <h2>Built to keep people<br />and proof in control.</h2>
              <p>Clear evidence and explicit human decisions are part of the workflow itself.</p>
            </div>
            <div className="trust-list">
              {[
                ['HUMAN IN THE LOOP', 'AI suggests. People decide. Approval records are immutable.'],
                ['YOUR DATA STAYS YOURS', 'Every query is limited to your own company.'],
                ['PRIVACY FIRST', 'Emails and phone numbers are removed before text reaches AI.'],
                ['ALWAYS AVAILABLE', 'Rule based checks keep working when AI is down.'],
              ].map(([label, body]) => (
                <div className="trust-item" key={label}>
                  <span className="trust-icon"><Check size={14} /></span>
                  <div><Label>{label}</Label><p>{body}</p></div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section faq-section" id="faq">
          <div className="container faq-layout">
            <div className="faq-title">
              <Label>07 / GOOD QUESTIONS</Label>
              <h2>Clarity, before<br />you get started.</h2>
              <p>Still curious? <a href="mailto:hello@mindvault.ai">Talk to the team <ArrowUpRight size={13} /></a></p>
            </div>
            <div className="faq-list">
              {faqs.map(([q, a], i) => (
                <details key={q} open={i === 0}>
                  <summary><span>{q}</span><span className="faq-toggle"><ChevronDown size={15} /></span></summary>
                  <p>{a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="final-cta">
          <div className="container final-inner">
            <div>
              <Label>MAKE THE NEXT DRAFT A BETTER ONE</Label>
              <h2>Run your first check<br />in under a minute.</h2>
              <p>Start with the Veyra Audio demo. Fictional data, clear evidence, human decisions.</p>
            </div>
            <div className="cta-stamp">
              <span>MV</span>
              <span>CHECK IT<br />BEFORE IT<br />GOES LIVE</span>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container">
          <div className="footer-main">
            <div className="footer-brand">
              <a href="#top" className="wordmark">
                <span className="brand-mark">m</span>
                <span>MINDVAULT<span className="wordmark-ai"> AI</span></span>
              </a>
              <p>Check it before<br />the world sees it.</p>
            </div>
            <div className="footer-col">
              <Label>EXPLORE</Label>
              <a href="#product">Product</a>
              <a href="#how">How it works</a>
              <a href="#roles">Roles</a>
              <a href="#faq">FAQ</a>
            </div>
            <div className="footer-col">
              <Label>INFORMATION</Label>
              <a href="#trust">Security</a>
              <a href="#trust">Privacy</a>
              <a href="#trust">Terms</a>
            </div>
          </div>
          <div className="footer-bottom">
            <span>© 2026 MINDVAULT AI</span>
            <span>BUILT FOR PEOPLE WHO CARE WHAT GOES OUT.</span>
            <a href="#top">BACK TO TOP ↑</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;

