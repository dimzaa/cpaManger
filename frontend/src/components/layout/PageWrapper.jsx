import React from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

export default function PageWrapper({ title, children, backPath = null }) {
  return (
    <div className="flex min-h-screen bg-gradient-to-b from-blue-50 via-gray-50 to-white">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 mr-sidebar">
        {/* TopBar */}
        <TopBar title={title} backPath={backPath} />

        {/* Page Content */}
        <main className="mt-topbar pt-24 pb-12 px-6">
          <div className="max-w-5xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
