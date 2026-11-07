import { useEffect,type ReactNode } from 'react';
import { Link,Route,Routes } from 'react-router-dom';
import { ApplicationShell } from './components/ApplicationShell';
import { ErrorBoundary,StatePanel } from './components/ui';
import { AuthProvider,useAuth } from './auth/AuthContext';
import { WorkspaceProvider } from './workspace/WorkspaceContext';
import { initials,type User } from './api/client';
import { apiJourneyService,apiQueueService,apiReviewService } from './services/api-workspace-services';
import { ConnectedContentCheckPage } from './features/content-check/ConnectedContentCheckPage';
import { ReviewerQueuePage } from './features/reviewer-queue/ReviewerQueuePage';
import { ReviewerDetailPage } from './features/reviewer-detail/ReviewerDetailPage';
import { RevisionJourneyPage } from './features/revision-journey/RevisionJourneyPage';
import { AuditPage,ClarityPage,DocumentsPage,EvaluationPage,ExtractionPage,KnowledgePage,OverviewPage,ProductsPage,SettingsPage,UploadPage } from './features/management/AdminPages';
import { LandingPage } from './landing/LandingPage';

function Allowed({roles,children}:{roles:User['role'][];children:ReactNode}){const {user}=useAuth();return user&&roles.includes(user.role)?children:<StatePanel title="This page is restricted"><p>Your account does not have permission for this action.</p><Link className="button button-primary" to="/dashboard">Back to overview</Link></StatePanel>;}
function WorkspaceRoutes(){
  const {user,health,logout}=useAuth();
  useEffect(()=>{if(user&&user.role!=='creator')void apiQueueService.load('default').catch(()=>{});},[user]);
  if(!user)return null;
  return <WorkspaceProvider><Routes><Route element={<ApplicationShell live role={user.role} demo={health?.demo_mode} onLogout={logout} workspaceName={user.org_name} profile={{name:user.name,title:user.role,initials:initials(user.name)}} queueService={apiQueueService}/>}>
    <Route index element={<OverviewPage/>}/>
    <Route path="dashboard" element={<OverviewPage/>}/>
    <Route path="overview" element={<OverviewPage/>}/>
    <Route path="brand-knowledge" element={<DocumentsPage/>}/><Route path="sources" element={<DocumentsPage sources/>}/>
    <Route path="upload" element={<Allowed roles={['admin']}><UploadPage/></Allowed>}/><Route path="extraction" element={<Allowed roles={['admin']}><ExtractionPage/></Allowed>}/>
    <Route path="compliance-rules" element={<KnowledgePage kind="rule"/>}/><Route path="facts" element={<KnowledgePage kind="fact"/>}/><Route path="products" element={<ProductsPage/>}/>
    <Route path="clarity" element={<Allowed roles={['admin']}><ClarityPage/></Allowed>}/><Route path="evaluation" element={<Allowed roles={['admin']}><EvaluationPage/></Allowed>}/>
    <Route path="audit-logs" element={<Allowed roles={['admin','reviewer']}><AuditPage/></Allowed>}/><Route path="settings" element={<SettingsPage/>}/><Route path="profile" element={<SettingsPage/>}/>
    <Route path="content-checks" element={<Allowed roles={['admin','creator']}><ConnectedContentCheckPage/></Allowed>}/>
    <Route path="approvals" element={<Allowed roles={['admin','reviewer']}><ReviewerQueuePage service={apiQueueService}/></Allowed>}/>
    <Route path="approvals/:submissionId" element={<ReviewerDetailPage service={apiReviewService}/>}/>
    <Route path="content/:contentId/history" element={<RevisionJourneyPage service={apiJourneyService}/>}/>
    <Route path="*" element={<StatePanel title="Page not found"><Link to="/dashboard">Return to dashboard</Link></StatePanel>}/>
  </Route></Routes></WorkspaceProvider>;
}
export function LiveApp(){
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard/*" element={<AuthProvider><WorkspaceRoutes /></AuthProvider>} />
        <Route path="/*" element={<AuthProvider><WorkspaceRoutes /></AuthProvider>} />
      </Routes>
    </ErrorBoundary>
  );
}
