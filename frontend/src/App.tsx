import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { useAuthStore, useLearningStore } from "./store";
import AppLayout from "./components/layout/AppLayout";
import LoginPage from "./pages/LoginPage";
import CodeWorkspace from "./components/code/CodeWorkspace";
import LearningPathView from "./components/path/LearningPathView";
import KnowledgeGraph from "./components/path/KnowledgeGraph";
import Dashboard from "./components/dashboard/Dashboard";
import ApiSettings from "./components/settings/ApiSettings";
import ErrorBoundary from "./components/common/ErrorBoundary";
import "./App.css";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loadUser } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) loadUser();
  }, []);

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function KnowledgeGraphRoute() {
  const { learningPath, loadLearningPath, currentKpId, setCurrentKpId } = useLearningStore();

  useEffect(() => {
    loadLearningPath();
  }, [loadLearningPath]);

  if (!learningPath) return <div className="loading">加载知识图谱中...</div>;

  return (
    <KnowledgeGraph
      nodes={learningPath.nodes}
      currentKpId={currentKpId}
      onSelectKp={setCurrentKpId}
    />
  );
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/learn" replace />} />
            <Route path="learn" element={<ErrorBoundary><CodeWorkspace /></ErrorBoundary>} />
            <Route path="path" element={<ErrorBoundary><LearningPathView /></ErrorBoundary>} />
            <Route path="graph" element={<ErrorBoundary><KnowledgeGraphRoute /></ErrorBoundary>} />
            <Route path="dashboard" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
            <Route path="settings" element={<ErrorBoundary><ApiSettings /></ErrorBoundary>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
