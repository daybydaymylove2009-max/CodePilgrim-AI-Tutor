import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { useAuthStore } from "./store";
import AppLayout from "./components/layout/AppLayout";
import LoginPage from "./pages/LoginPage";
import CodeWorkspace from "./components/code/CodeWorkspace";
import LearningPathView from "./components/path/LearningPathView";
import Dashboard from "./components/dashboard/Dashboard";
import "./App.css";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loadUser } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) loadUser();
  }, []);

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  return (
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
          <Route path="learn" element={<CodeWorkspace />} />
          <Route path="path" element={<LearningPathView />} />
          <Route path="dashboard" element={<Dashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
