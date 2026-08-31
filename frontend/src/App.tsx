import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout/AppLayout";
import { ClipDetailPage } from "@/pages/ClipDetailPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LibraryPage } from "@/pages/LibraryPage";
import { UploadPage } from "@/pages/UploadPage";
import { VideoProcessingPage } from "@/pages/VideoProcessingPage";

/**
 * Top-level route table. No authentication in this MVP (see CLAUDE.md /
 * INITIAL.md), so there is no ProtectedRoute wrapper or AuthProvider here.
 */
export default function App() {
  return (
    <Router>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/videos/:id/processing" element={<VideoProcessingPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/library/:clipId" element={<ClipDetailPage />} />
        </Route>
      </Routes>
    </Router>
  );
}
