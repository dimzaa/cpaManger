import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function MunicipalityRoute() {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-neutral-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-neutral-600 font-hebrew">טוען...</p>
        </div>
      </div>
    );
  }

  // Not logged in — redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Admin users should use /dashboard, not /portal
  if (user?.role === 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  // Municipality users and employees are allowed
  if (user?.role === 'municipality' || user?.role === 'employee') {
    return <Outlet />;
  }

  // Unknown role — redirect to login
  return <Navigate to="/login" replace />;
}
