import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import PortalSidebar from './PortalSidebar';
import PortalTopBar from './PortalTopBar';

export default function PortalWrapper({ title, children, onBack }) {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const handleBack = onBack ? onBack : null;

  return (
    <div className="flex min-h-screen bg-gradient-to-b from-blue-50 via-gray-50 to-white">
      {/* Sidebar */}
      <PortalSidebar onLogout={handleLogout} />

      {/* Main Content */}
      <div className="flex-1 mr-64">
        {/* TopBar */}
        <PortalTopBar title={title} onBack={handleBack} />

        {/* Page Content - Centered Container */}
        <main className="pt-24 pb-12">
          <div className="max-w-5xl mx-auto px-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
