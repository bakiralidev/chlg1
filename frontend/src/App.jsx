import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { Toaster } from 'react-hot-toast';

// Public Landing page
import Landing from './pages/Landing';

// Auth pages
import Login from './pages/Login';
import SetPassword from './pages/SetPassword';

// User pages
import Dashboard from './pages/Dashboard';
import ChallengeRoadmap from './pages/ChallengeRoadmap';
import Results from './pages/Results';
import Arena from './pages/Arena';

// Admin pages
import AdminDashboard from './pages/admin/AdminDashboard';
import ChallengeForm from './pages/admin/ChallengeForm';
import DayManager from './pages/admin/DayManager';
import QuestionForm from './pages/admin/QuestionForm';
import ScoreImport from './pages/admin/ScoreImport';
import ParticipantsList from './pages/admin/ParticipantsList';
import SubmissionsReview from './pages/admin/SubmissionsReview';
import SuspiciousActivity from './pages/admin/SuspiciousActivity';

// Components
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e1e2e',
            color: '#cdd6f4',
            border: '1px solid #313244',
          },
        }}
      />
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/set-password" element={<SetPassword />} />

        {/* Protected user routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/challenge/:challengeId" element={<ChallengeRoadmap />} />
          <Route path="/challenge/:challengeId/results" element={<Results />} />
          <Route path="/arena/:dayId" element={<Arena />} />
        </Route>

        {/* Admin routes */}
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/challenge/new" element={<ChallengeForm />} />
          <Route path="/admin/challenge/:id/edit" element={<ChallengeForm />} />
          <Route path="/admin/challenge/:id/days" element={<DayManager />} />
          <Route path="/admin/challenge/:challengeId/questions" element={<QuestionForm />} />
          <Route path="/admin/participants" element={<ParticipantsList />} />
          <Route path="/admin/submissions" element={<SubmissionsReview />} />
          <Route path="/admin/scores" element={<ScoreImport />} />
          <Route path="/admin/suspicious" element={<SuspiciousActivity />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
