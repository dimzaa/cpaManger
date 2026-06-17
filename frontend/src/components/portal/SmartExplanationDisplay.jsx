import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

/**
 * SmartExplanationDisplay — Shows formula breakdowns with color coding,
 * constants highlighting, and change detection.
 * 
 * Props:
 *   - explanation: Smart explanation object with summary, formula, why_changed
 *   - estimatedJobsChange: Estimated job change calculation (if applicable)
 */
export default function SmartExplanationDisplay({ explanation, estimatedJobsChange }) {
  const [isFormulaOpen, setIsFormulaOpen] = useState(false);
  const [isChangesOpen, setIsChangesOpen] = useState(false);

  if (!explanation) return null;

  const summary = explanation.summary || {};
  const formula = explanation.formula;
  const changes = explanation.why_changed;

  // Map color names to Tailwind classes
  const getColorClass = (color) => {
    const colorMap = {
      'blue': 'text-blue-700 bg-blue-50 border-l-4 border-blue-400',
      'orange': 'text-orange-700 bg-orange-50 border-l-4 border-orange-400',
      'green-bold': 'text-green-700 font-bold',
      'red-bold': 'text-red-700 font-bold',
      'purple-bold': 'text-purple-700 font-bold',
      'green': 'text-green-700',
      'red': 'text-red-700',
      'gray': 'text-gray-700',
    };
    return colorMap[color] || 'text-gray-700';
  };

  const getSummaryBoxColor = (boxColor) => {
    const boxColorMap = {
      'amber': 'bg-amber-50 border-l-4 border-amber-400',
      'red': 'bg-red-50 border-l-4 border-red-400',
      'green': 'bg-green-50 border-l-4 border-green-400',
      'blue': 'bg-blue-50 border-l-4 border-blue-400',
      'gray': 'bg-gray-50 border-l-4 border-gray-400',
    };
    return boxColorMap[boxColor] || 'bg-gray-50';
  };

  return (
    <div className="space-y-4">
      {/* LAYER 1: Summary Box */}
      {summary.text && (
        <div className={`p-4 rounded-lg ${getSummaryBoxColor(summary.color_box)}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{summary.icon}</span>
              <div>
                <p className="font-hebrew font-medium text-slate-900">{summary.text}</p>
                {summary.amount && (
                  <p className="text-sm text-slate-600 font-medium">{summary.amount}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* LAYER 2: Formula Breakdown (Collapsible) */}
      {formula && (
        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setIsFormulaOpen(!isFormulaOpen)}
            className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition"
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">📐</span>
              <span className="font-hebrew font-medium text-slate-900">איך חושב הסכום?</span>
            </div>
            <ChevronDown
              size={20}
              className={`text-slate-600 transition-transform ${isFormulaOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {isFormulaOpen && (
            <div className="p-6 bg-white space-y-4 border-t border-slate-200">
              {/* Formula text */}
              <p className="font-hebrew text-slate-900 font-semibold text-center">
                {formula.formula_text}
              </p>

              {/* Components breakdown */}
              <div className="space-y-3">
                {formula.components.map((component, idx) => (
                  <div key={idx} className={`p-3 rounded-lg ${getColorClass(component.color)}`}>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-hebrew font-medium">{component.label}</p>
                        <p className="text-sm font-hebrew mt-1">
                          <span className="font-bold text-lg">{component.value}</span>
                        </p>
                      </div>
                      {component.is_constant && component.tooltip && (
                        <div className="relative group ml-4">
                          <span className="cursor-help text-lg">ℹ️</span>
                          <div className="absolute right-0 bottom-full mb-2 w-48 p-3 bg-slate-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                            {component.tooltip}
                            <div className="absolute left-1/2 top-full transform -translate-x-1/2 border-4 border-transparent border-t-slate-900"></div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Result line */}
              <div className="flex items-center justify-center gap-4 pt-4 border-t border-slate-200">
                <span className="text-lg">=</span>
                <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 flex-1">
                  <p className="font-hebrew text-sm text-slate-600">סכום סופי</p>
                  <p className="text-xl font-bold text-blue-700">
                    {formula.components.find(c => c.position === 'result')?.value || 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* LAYER 3: Why It Changed (Collapsible) */}
      {changes && changes.has_changes && (
        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setIsChangesOpen(!isChangesOpen)}
            className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition"
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">📊</span>
              <span className="font-hebrew font-medium text-slate-900">מה השתנה מהחודש הקודם?</span>
            </div>
            <ChevronDown
              size={20}
              className={`text-slate-600 transition-transform ${isChangesOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {isChangesOpen && (
            <div className="p-6 bg-white space-y-4 border-t border-slate-200">
              {changes.explanations.map((exp, idx) => (
                <div key={idx} className="border border-blue-200 rounded-lg p-4 bg-blue-50">
                  <h4 className="font-hebrew font-bold text-slate-900 flex items-center gap-2 mb-2">
                    {exp.title}
                  </h4>
                  <p className="font-hebrew text-slate-700 mb-2">{exp.description}</p>
                  {exp.calculation && (
                    <p className="font-hebrew text-sm bg-white rounded p-2 mb-2 border-l-4 border-blue-400">
                      <span className="font-bold">חישוב:</span> {exp.calculation}
                    </p>
                  )}
                  {exp.change_amount && (
                    <div className="grid grid-cols-2 gap-2 text-sm font-hebrew mb-2">
                      <div>
                        <span className="text-slate-600">שינוי:</span>
                        <p className="font-bold text-blue-700">{exp.change_amount}</p>
                      </div>
                      <div>
                        <span className="text-slate-600">אחוז:</span>
                        <p className="font-bold text-blue-700">{exp.change_percentage}</p>
                      </div>
                    </div>
                  )}
                  {exp.reason && (
                    <p className="font-hebrew text-sm text-slate-600 bg-white rounded p-2 border-l-4 border-green-400">
                      <span className="font-bold">סיבה אפשרית:</span> {exp.reason}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Estimated Jobs Change (if applicable) */}
      {estimatedJobsChange && (
        <div className="border-l-4 border-amber-400 bg-amber-50 p-4 rounded-lg">
          <div className="flex items-start gap-3">
            <span className="text-2xl">💼</span>
            <div>
              <h4 className="font-hebrew font-bold text-slate-900 mb-2">שינוי משרות אפשרי</h4>
              <p className="font-hebrew text-slate-700 mb-2">
                הסכום עלה ב-<span className="font-bold">{estimatedJobsChange.amount_change}</span> — זה מתאים ל-
                <span className="font-bold text-blue-700 mx-1">{estimatedJobsChange.estimated_positions}</span>
                משרות בעלות <span className="font-bold">{estimatedJobsChange.cost_per_position}</span> למשרה
              </p>
              <p className="font-hebrew text-sm text-amber-700 bg-white rounded p-2">
                {estimatedJobsChange.warning}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
