import "./App.css";
import { useEffect } from "react";
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";

const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/dashboard", element: <Dashboard /> }
]);

export default function App() {
  return <RouterProvider router={router} />;
}

import { AuthProvider, useAuth } from "./context/AuthContext";
import { Toaster } from "sonner";
import { toast } from "sonner";

// Pages
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import DevPortal from "./pages/DevPortal";
import DevLogin from "./pages/DevLogin";
import TransakDemo from "./pages/TransakDemo";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import ChangePassword from "./pages/ChangePassword";
import Admin from "./pages/Admin";
import Onboarding from "./pages/Onboarding";

// Protected Route Component
function ProtectedRoute({ children, requireDeveloper = false }) {
  const { isAuthenticated, isDeveloper, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requireDeveloper && !isDeveloper) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

// Public Route (redirect if logged in)
function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function AppRoutes() {
  const navigate = useNavigate();

  // Global KYC-required interceptor: any 403 with {error:'kyc_required'}
  // from the backend triggers a toast + redirect to /onboarding so the
  // user always knows why a transaction was blocked.
  useEffect(() => {
    const handler = (e) => {
      const status = e.detail?.kyc_status || 'NOT_STARTED';
      toast.error('KYC verification required', {
        description: `Status: ${status} — complete identity verification to transact.`,
        action: { label: 'Verify now', onClick: () => navigate('/onboarding') },
      });
      // Best-effort auto-redirect for the no-action case
      setTimeout(() => navigate('/onboarding'), 1500);
    };
    window.addEventListener('neonoble:kyc-required', handler);
    return () => window.removeEventListener('neonoble:kyc-required', handler);
  }, [navigate]);

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Home />} />
      
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />
      
      <Route
        path="/signup"
        element={
          <PublicRoute>
            <Signup />
          </PublicRoute>
        }
      />
      
      <Route
        path="/dev/login"
        element={
          <PublicRoute>
            <DevLogin />
          </PublicRoute>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      {/* Developer Portal (requires developer role) */}
      <Route
        path="/dev"
        element={
          <ProtectedRoute requireDeveloper>
            <DevPortal />
          </ProtectedRoute>
        }
      />

      {/* Transak compliance demo (auth not required — non-custodial demo flow) */}
      <Route path="/transak" element={<TransakDemo />} />

      {/* Password recovery */}
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route
        path="/change-password"
        element={
          <ProtectedRoute>
            <ChangePassword />
          </ProtectedRoute>
        }
      />

      {/* CASP Admin Console */}
      <Route path="/admin/*" element={<Admin />} />

      {/* Customer Onboarding (self-service KYC) */}
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <Onboarding />
          </ProtectedRoute>
        }
      />

      {/* Catch all - redirect to home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
          <Toaster />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
