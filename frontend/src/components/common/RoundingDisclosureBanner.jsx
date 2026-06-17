import React from 'react';

export default function RoundingDisclosureBanner({ text }) {
  if (!text) return null;

  return (
    <div className="bg-slate-50 border border-slate-200 text-slate-700 text-sm font-hebrew px-4 py-2 rounded-lg" dir="rtl">
      {text}
    </div>
  );
}
