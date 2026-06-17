import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

export default function RetroExplainer() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mb-8 bg-blue-50 border-r-4 border-blue-400 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-blue-100 transition"
      >
        <div className="flex items-center gap-3 text-right flex-1">
          <span className="text-2xl">💡</span>
          <h3 className="font-hebrew font-bold text-lg text-neutral-900">מה זה תשלום רטרואקטיבי?</h3>
        </div>
        <ChevronDown
          size={20}
          className={`text-blue-600 transition ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {expanded && (
        <div className="px-6 py-4 border-t border-blue-200">
          <p className="font-hebrew text-neutral-700 leading-relaxed">
            תשלום רטרואקטיבי הוא סכום שמשרד החינוך העביר לעיריה בחודש זה, עבור חודש שעבר או חודשים קודמים. זה קורה כאשר תשלום אושר באיחור או תוקן לאחר מועד הביצוע המקורי.
            <br />
            <br />
            לדוגמה: אם בחודש מרץ קיבלתם תשלום עבור ינואר שלא בוצע בעבר, זה יופיע כ"רטרו" בדוח של מרץ.
          </p>
        </div>
      )}
    </div>
  );
}
