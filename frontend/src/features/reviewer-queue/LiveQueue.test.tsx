// @vitest-environment jsdom
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {ReviewerQueuePage} from './ReviewerQueuePage';
import type {QueueSubmission,ReviewerQueueService} from '../../types/reviewer-queue';
vi.mock('../../components/ShellHeader',()=>({ShellHeader:({children}:{children:React.ReactNode})=><header>{children}</header>}));
afterEach(cleanup);
it('links a persisted approved queue row to its approved snapshot rather than a newer draft',async()=>{
  const records:QueueSubmission[]=[{id:'content-1',revisionId:'approved-v2',title:'Previously approved caption',campaign:'Campaign',assetDescription:'Revision 2',brand:'Brand',submittedBy:{name:'Writer',team:'Creator',initials:'WR'},channel:'instagram',region:'IN',submittedAt:Date.now(),approvedAt:Date.now(),status:'approved',severity:'none',statusLabel:'Approved',summary:'Saved approval',origin:'api',simulated:false}];
  const service:ReviewerQueueService={mode:'api',load:async()=>records,subscribe:()=>()=>{},getSnapshot:()=>records,getHistory:()=>({reviewedBeforeVisibleQueue:0,approvedYesterday:0})};
  render(<MemoryRouter initialEntries={['/approvals?status=approved']}><ReviewerQueuePage service={service}/></MemoryRouter>);
  const link=await screen.findByRole('link',{name:'Previously approved caption'});
  const url=new URL(link.getAttribute('href')!,'http://localhost');expect(url.pathname).toBe('/approvals/content-1');expect(url.searchParams.get('revision')).toBe('approved-v2');
});
