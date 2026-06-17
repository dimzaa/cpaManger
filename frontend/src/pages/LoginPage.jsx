import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Eye, EyeOff } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loading, error } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [validationError, setValidationError] = useState('');

  const validateForm = () => {
    if (!email.includes('@')) {
      setValidationError('אנא הזן כתובת דוא״ל תקינה');
      return false;
    }
    if (password.length < 6) {
      setValidationError('הסיסמה חייבת להיות לפחות 6 תווים');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError('');

    if (!validateForm()) return;

    try {
      const userData = await login(email, password);
      // Redirect based on user role
      if (userData?.role === 'admin') {
        navigate('/dashboard');
      } else if (userData?.role === 'municipality') {
        navigate('/portal');
      } else {
        navigate('/login');
      }
    } catch (err) {
      // Error already set by useAuth
    }
  };

  const displayError = validationError || error;

  return (
    <div className="min-h-screen flex">
      {/* Left side - Brand */}
      <div className="hidden md:flex md:w-1/2 bg-primary-500 text-white items-center justify-center p-12 flex-col">
        <h1 className="text-5xl font-hebrew font-bold mb-4">SmartHub</h1>
        <p className="text-xl text-primary-100 text-center font-hebrew">
          פלטפורמה לניהול תקציב משרד החינוך
        </p>
        <p className="text-sm text-primary-200 mt-8 text-center max-w-xs">
          ניהול וביקורת של תקציבים עירוניים באופן מרכזי ויעיל
        </p>
      </div>

      {/* Right side - Login Form */}
      <div className="w-full md:w-1/2 bg-neutral-50 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-hebrew font-bold text-neutral-900 mb-2">
              כניסה לחשבון
            </h2>
            <p className="text-neutral-600">הזן את פרטיך כדי להמשיך</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email Field */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                דוא״ל
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-right"
              />
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                סיסמה
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="הזן סיסמה"
                  className="w-full px-4 py-3 pr-10 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-right"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-700"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {displayError && (
              <div className="p-4 bg-danger/10 border border-danger text-danger rounded-lg text-sm flex gap-2">
                <span>⚠️</span>
                <span>{displayError}</span>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-3 bg-primary-500 hover:bg-primary-light text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>מעבד...</span>
                </>
              ) : (
                'כניסה לחשבון'
              )}
            </button>
          </form>

          {/* Demo Credentials Info */}
          <div className="mt-10 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm">
            <p className="font-medium text-blue-900 mb-2">אישור מנהל (להדגמה):</p>
            <div className="space-y-1 text-blue-800 text-xs font-mono">
              <p>דוא״ל: admin@example.com</p>
              <p>סיסמה: admin123</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
