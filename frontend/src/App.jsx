import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import DatasetsPage from './pages/DatasetsPage';
import GraphPage from './pages/GraphPage';
import TypesPage from './pages/TypesPage';
import InstancesPage from './pages/InstancesPage';
import ModelingPage from './pages/ModelingPage';
import QuickModelingPage from './pages/QuickModelingPage';
import StructureChangesPage from './pages/StructureChangesPage';
import DataSyncPage from './pages/DataSyncPage';
import VersionsPage from './pages/VersionsPage';
import PermissionsPage from './pages/PermissionsPage';
import DataManagementPage from './pages/DataManagementPage';
import RagKnowledgeBase from './pages/RagKnowledgeBase';
import RagChat from './pages/RagChat';
import RetrievalPage from './pages/RetrievalPage';
import RagModelConfigPage from './pages/RagModelConfigPage';
import ServiceConfigPage from './pages/ServiceConfigPage';
import RagEvalPage from './pages/RagEvalPage';
import GraphRAGKnowledgeBase from './pages/GraphRAGKnowledgeBase';
import GraphRAGDocuments from './pages/GraphRAGDocuments';
import GraphRAGGraph from './pages/GraphRAGGraph';
import GraphRAGQA from './pages/GraphRAGQA';
import GraphRAGModelConfig from './pages/GraphRAGModelConfig';
import SkillsPage from './pages/SkillsPage';
import UsersPage from './pages/UsersPage';
import RolesPage from './pages/RolesPage';
import GroupsPage from './pages/GroupsPage';
import AdminTokensPage from './pages/AdminTokensPage';
import ACRPage from './pages/ACRPage';
import SystemConfigPage from './pages/SystemConfigPage';
import ApiKeysPage from './pages/ApiKeysPage';
import PersonalTokensPage from './pages/PersonalTokensPage';
import ProfilePage from './pages/ProfilePage';
import HealthPage from './pages/HealthPage';

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#7c3aed',
          borderRadius: 6,
          fontFamily: "'Inter', -apple-system, sans-serif",
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="datasets" element={<DatasetsPage />} />
            {/* RAG */}
            <Route path="ragflow/knowledge-base" element={<RagKnowledgeBase />} />
            <Route path="ragflow/chat" element={<RagChat />} />
            <Route path="ragflow/retrieval" element={<RetrievalPage />} />
            <Route path="rag-evaluation" element={<RagEvalPage />} />
            <Route path="ragflow/model-config" element={<RagModelConfigPage />} />
            <Route path="ragflow/service-config" element={<ServiceConfigPage />} />
            {/* ONTOLOGY */}
            <Route path="ontology/graph" element={<GraphPage />} />
            <Route path="ontology/types" element={<TypesPage />} />
            <Route path="ontology/instances" element={<InstancesPage />} />
            <Route path="ontology/modeling" element={<ModelingPage />} />
            <Route path="ontology/quick-modeling" element={<QuickModelingPage />} />
            <Route path="ontology/structure-changes" element={<StructureChangesPage />} />
            <Route path="ontology/data-sync" element={<DataSyncPage />} />
            <Route path="ontology/versions" element={<VersionsPage />} />
            <Route path="ontology/permissions" element={<PermissionsPage />} />
            {/* GRAPHRAG */}
            <Route path="graphrag/knowledge-base" element={<GraphRAGKnowledgeBase />} />
            <Route path="graphrag/documents" element={<GraphRAGDocuments />} />
            <Route path="graphrag/graph" element={<GraphRAGGraph />} />
            <Route path="graphrag/qa" element={<GraphRAGQA />} />
            <Route path="graphrag/model-config" element={<GraphRAGModelConfig />} />
            {/* SKILLS + ADMIN */}
            <Route path="skills" element={<SkillsPage />} />
            <Route path="admin/users" element={<UsersPage />} />
            <Route path="admin/roles" element={<RolesPage />} />
            <Route path="admin/groups" element={<GroupsPage />} />
            <Route path="admin/tokens" element={<AdminTokensPage />} />
            <Route path="admin/acr" element={<ACRPage />} />
            <Route path="admin/system-config" element={<SystemConfigPage />} />
            <Route path="api-keys" element={<ApiKeysPage />} />
            <Route path="personal-tokens" element={<PersonalTokensPage />} />
            {/* Profile + Health */}
            <Route path="profile" element={<ProfilePage />} />
            <Route path="health" element={<HealthPage />} />
          </Route>
          <Route path="/403" element={<ProtectedRoute><AppLayout /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
