import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { api } from "./api/client";
import { Layout, LoadingBlock } from "./components/Layout";
import AuthPage from "./pages/AuthPage";
import CreateProjectPage from "./pages/CreateProjectPage";
import DashboardPage from "./pages/DashboardPage";
import JobStatusPage from "./pages/JobStatusPage";
import LessonPage from "./pages/LessonPage";
import MistakesPage from "./pages/MistakesPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ReviewsPage from "./pages/ReviewsPage";

function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  if (me.isLoading) {
    return (
      <div className="min-h-screen bg-paper p-6">
        <LoadingBlock label="Checking session" />
      </div>
    );
  }
  if (me.isError) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/new"
        element={
          <RequireAuth>
            <CreateProjectPage />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:projectId"
        element={
          <RequireAuth>
            <ProjectDetailPage />
          </RequireAuth>
        }
      />
      <Route
        path="/jobs/:jobId"
        element={
          <RequireAuth>
            <JobStatusPage />
          </RequireAuth>
        }
      />
      <Route
        path="/lessons/:lessonId"
        element={
          <RequireAuth>
            <LessonPage />
          </RequireAuth>
        }
      />
      <Route
        path="/reviews"
        element={
          <RequireAuth>
            <ReviewsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/mistakes"
        element={
          <RequireAuth>
            <MistakesPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
