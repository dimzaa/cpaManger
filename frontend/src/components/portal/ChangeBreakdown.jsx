/**
 * ChangeBreakdown Component
 * 
 * Displays a detailed breakdown of all changes detected between
 * the current month's budget and the previous month's budget.
 * 
 * Shows:
 * - All detected changes (children count, costs, percentages, etc.)
 * - Financial impact of each change
 * - Total impact across all changes
 * - Visual indicators for different change types
 */

import React from 'react';
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

export default function ChangeBreakdown({ 
  changes = [],
  totalImpact = null,
  month,
  topicCode,
  topicName,
  isLoading = false
}) {
  
  // Group changes by type
  const groupedChanges = {
    numeric: changes.filter(c => c.change_type === 'numeric'),
    categorical: changes.filter(c => c.change_type === 'categorical'),
    grant_status: changes.filter(c => c.change_type === 'grant_status'),
    retro: changes.filter(c => c.change_type === 'retro'),
  };

  const hasChanges = changes && changes.length > 0;

  // Loading state
  if (isLoading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 animate-pulse">
        <div className="h-4 bg-gray-300 rounded w-1/3 mb-2"></div>
        <div className="h-4 bg-gray-300 rounded w-1/4"></div>
      </div>
    );
  }

  // No changes state
  if (!hasChanges) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-green-700">
          <span className="text-2xl">✓</span>
          <p className="font-hebrew text-sm">אין שינויים בשורה זו בהשוואה לחודש הקודם</p>
        </div>
      </div>
    );
  }

  // Render a single change item
  const ChangeItem = ({ change }) => {
    const isIncrease = 
      (change.change_type === 'numeric' && 
       parseFloat(change.current?.replace(/₪|,|%/g, '')) >= parseFloat(change.previous?.replace(/₪|,|%/g, '')));

    return (
      <div className="bg-white rounded p-3 border border-gray-200 mb-2 last:mb-0">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {/* Main description */}
            <p className="font-hebrew text-sm text-gray-800 font-semibold mb-1">
              {change.hebrew_description}
            </p>
            
            {/* Before/After values */}
            <div className="flex items-center gap-2 text-xs font-hebrew text-gray-600">
              <span>
                <strong>מ:</strong> 
                <span className="mr-1 text-gray-700">{change.previous}</span>
              </span>
              <span className="text-gray-400">→</span>
              <span>
                <strong>ל:</strong> 
                <span className="mr-1 text-gray-700">{change.current}</span>
              </span>
            </div>
          </div>
          
          {/* Impact badge */}
          <div className="ml-2 text-right">
            {change.impact_shekel && (
              <div className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-hebrew font-semibold ${
                isIncrease 
                  ? 'bg-red-100 text-red-700'
                  : 'bg-green-100 text-green-700'
              }`}>
                {isIncrease ? (
                  <TrendingUp size={12} />
                ) : (
                  <TrendingDown size={12} />
                )}
                {change.impact_shekel}
              </div>
            )}
            {change.impact_pct && !change.impact_shekel && (
              <div className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-hebrew font-semibold bg-blue-100 text-blue-700">
                {change.impact_pct > 0 ? '+' : ''}{change.impact_pct.toFixed(1)}%
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Render changes grouped by category
  const ChangeSection = ({ title, icon, changes: sectionChanges, color }) => {
    if (!sectionChanges || sectionChanges.length === 0) return null;

    return (
      <div className="mb-4">
        <div className={`flex items-center gap-2 mb-2 pb-2 border-b-2 border-${color}-200`}>
          <span className={`text-${color}-600`}>{icon}</span>
          <h4 className={`font-hebrew font-semibold text-sm text-${color}-900`}>
            {title}
          </h4>
          <span className={`ml-auto text-xs bg-${color}-100 text-${color}-700 px-2 py-1 rounded-full font-hebrew`}>
            {sectionChanges.length}
          </span>
        </div>
        <div className="space-y-2">
          {sectionChanges.map((change, idx) => (
            <ChangeItem key={idx} change={change} />
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="rounded-lg border border-gray-300 p-4 bg-gray-50">
      {/* Header */}
      <div className="mb-4 pb-3 border-b border-gray-300">
        <h3 className="font-hebrew font-bold text-gray-800 text-sm mb-1">
          📊 פירוט שינויים בשורה
        </h3>
        <p className="font-hebrew text-xs text-gray-600">
          {topicName} (קוד {topicCode}) — חודש {month}
        </p>
      </div>

      {/* Changes by category */}
      <div>
        <ChangeSection
          title="שינויים מספריים"
          icon="🔢"
          changes={groupedChanges.numeric}
          color="blue"
        />
        
        <ChangeSection
          title="שינויים קטגוריאליים"
          icon="🏷️"
          changes={groupedChanges.categorical}
          color="purple"
        />
        
        <ChangeSection
          title="שינויים בזכאות למענק"
          icon="🎁"
          changes={groupedChanges.grant_status}
          color="yellow"
        />
        
        <ChangeSection
          title="תשלומים רטרואקטיביים"
          icon="↩️"
          changes={groupedChanges.retro}
          color="orange"
        />
      </div>

      {/* Total impact summary */}
      {totalImpact && totalImpact !== '₪0' && (
        <div className="mt-4 pt-4 border-t border-gray-300 bg-white rounded p-3">
          <div className="flex items-center justify-between">
            <h4 className="font-hebrew font-semibold text-gray-800 text-sm">
              סה""כ השפעה כלכלית:
            </h4>
            <div className="text-lg font-bold text-gray-900 font-monospace">
              {totalImpact}
            </div>
          </div>
        </div>
      )}

      {/* Info footer */}
      <div className="mt-3 pt-3 border-t border-gray-200">
        <p className="font-hebrew text-xs text-gray-500">
          💡 שינויים אלה זוהו באופן אוטומטי על ידי השוואת הנתונים לחודש הקודם. 
          בדוק שהם משקפים את התוכן שלך.
        </p>
      </div>
    </div>
  );
}
