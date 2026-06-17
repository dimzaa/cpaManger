import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AdminRoute from './guards/AdminRoute';
import MunicipalityRoute from './guards/MunicipalityRoute';

// CPA Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import MunicipalityPage from './pages/MunicipalityPage';
import AdminBudgetDetailPage from './pages/AdminBudgetDetailPage';
import ComparePage from './pages/ComparePage';
import AdminEmployeesPage from './pages/AdminEmployeesPage';
import AdminPresetsPage from './pages/AdminPresetsPage';
import AdminApprovalsPage from './pages/AdminApprovalsPage';
import AdminPositionsPage from './pages/AdminPositionsPage';
import AdminAnalyticsPage from './pages/AdminAnalyticsPage';
import AdminReportsPage from './pages/AdminReportsPage';
import AdminRemindersPage from './pages/AdminRemindersPage';
import AdminMinistryPage from './pages/AdminMinistryPage';

// Municipality Portal Pages
import PortalHomePage from './pages/PortalHomePage';
import PortalBudgetPage from './pages/PortalBudgetPage';
import EmployeeRejectedPage from './pages/EmployeeRejectedPage';
import PortalPositionsPage from './pages/PortalPositionsPage';
import PortalAnalyticsPage from './pages/PortalAnalyticsPage';
import EmployeeSuggestionsPage from './pages/EmployeeSuggestionsPage';
import ReportsPage from './pages/ReportsPage';
import PortalDeadlinesPage from './pages/PortalDeadlinesPage';
import PortalMinistryPage from './pages/PortalMinistryPage';

function AppContent() {
  const { isAuthenticated, loading, user } = useAuth();

  console.log('[AppContent] render', {
    path: window.location.pathname,
    isAuthenticated,
    role: user?.role,
    loading,
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-b from-blue-50 via-gray-50 to-white">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-neutral-600 font-hebrew">טוען...</p>
        </div>
      </div>
    );
  }

  // Redirect authenticated users based on role
  const getAuthenticatedRedirect = () => {
    if (user?.role === 'admin') return '/dashboard';
    if (user?.role === 'municipality') return '/portal';
    if (user?.role === 'employee') return '/portal';
    return '/login';
  };

  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen bg-gradient-to-b from-blue-50 via-gray-50 to-white">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-neutral-600 font-hebrew">טוען עמוד...</p>
          </div>
        </div>
      }
    >
      <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to={getAuthenticatedRedirect()} replace /> : <LoginPage />}
      />

      {/* Admin Routes */}
      <Route path="/dashboard">
        <Route
          index
          element={
            <AdminRoute>
              <DashboardPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/upload">
        <Route
          index
          element={
            <AdminRoute>
              <UploadPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/municipality/:id">
        <Route
          index
          element={
            <AdminRoute>
              <MunicipalityPage />
            </AdminRoute>
          }
        />
        <Route
          path="detail"
          element={
            <AdminRoute>
              <AdminBudgetDetailPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/compare/:id">
        <Route
          index
          element={
            <AdminRoute>
              <ComparePage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/admin/employees">
        <Route
          index
          element={
            <AdminRoute>
              <AdminEmployeesPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/admin/presets">
        <Route
          index
          element={
            <AdminRoute>
              <AdminPresetsPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/admin/approvals">
        <Route
          index
          element={
            <AdminRoute>
              <AdminApprovalsPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/admin/positions">
        <Route
          index
          element={
            <AdminRoute>
              <AdminPositionsPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/admin/analytics">
        <Route
          index
          element={
            <AdminRoute>
              <AdminAnalyticsPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/admin/reports">
        <Route
          index
          element={
            <AdminRoute>
              <AdminReportsPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/admin/reminders">
        <Route
          index
          element={
            <AdminRoute>
              <AdminRemindersPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/admin/ministry">
        <Route
          index
          element={
            <AdminRoute>
              <AdminMinistryPage />
            </AdminRoute>
          }
        />
      </Route>

      {/* Municipality Portal Routes */}
      <Route path="/portal" element={<MunicipalityRoute />}>
        <Route index element={<PortalHomePage />} />
        <Route path="budget" element={<PortalBudgetPage />} />
        <Route path="rejected" element={<EmployeeRejectedPage />} />
        <Route path="positions" element={<PortalPositionsPage />} />
        <Route path="analytics" element={<PortalAnalyticsPage />} />
        <Route path="suggestions" element={<EmployeeSuggestionsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="deadlines" element={<PortalDeadlinesPage />} />
        <Route path="ministry" element={<PortalMinistryPage />} />
      </Route>

      {/* Fallback */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </BrowserRouter>
  );
}
