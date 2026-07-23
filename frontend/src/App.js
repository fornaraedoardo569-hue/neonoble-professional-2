import "./App.css";
import { useEffect } from "react";
import {
  RouterProvider,
  createBrowserRouter,
  Navigate,
  useNavigate,
} from "react-router-dom";

import { AuthProvider, useAuth } from "./context/AuthContext";
import { Toaster, toast } from "sonner";

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

// Protected Route
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

// Public Route
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

// KYC Interceptor
function KycInterceptor({ children }) {
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e) => {
      const status = e.detail?.kyc_status || "NOT_STARTED";

      toast.error("KYC verification required", {
        description: `Status: ${status} — complete identity verification to transact.`,
        action: {
          label: "Verify now",
          onClick: () => navigate("/onboarding"),
        },
      });

      setTimeout(() => navigate("/onboarding"), 1500);
    };

    window.addEventListener("neonoble:kyc-required", handler);
    return () => window.removeEventListener("neonoble:kyc-required", handler);
  }, [navigate]);

  return children;
}

// Router v7
const router = createBrowserRouter([
  { path: "/", element: <Home /> },

  {
    path: "/login",
    element: (
      <PublicRoute>
        <Login />
      </PublicRoute>
    ),
  },

  {
    path: "/signup",
    element: (
      <PublicRoute>
        <Signup />
      </PublicRoute>
    ),
  },

  {
    path: "/dev/login",
    element: (
      <PublicRoute>
        <DevLogin />
      </PublicRoute>
    ),
  },

  {
    path: "/dashboard",
    element: (
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    ),
  },

  {
    path: "/dev",
    element: (
      <ProtectedRoute requireDeveloper>
        <DevPortal />
      </ProtectedRoute>
    ),
  },

  { path: "/transak", element: <TransakDemo /> },

  { path: "/forgot-password", element: <ForgotPassword /> },
  { path: "/reset-password", element: <ResetPassword /> },

  {
    path: "/change-password",
    element: (
      <ProtectedRoute>
        <ChangePassword />
      </ProtectedRoute>
    ),
  },

  { path: "/admin/*", element: <Admin /> },

  {
    path: "/onboarding",
    element: (
      <ProtectedRoute>
        <Onboarding />
      </ProtectedRoute>
    ),
  },

  { path: "*", element: <Navigate to="/" replace /> },
]);

// App wrapper
function App() {
  return (
    <AuthProvider>
      <KycInterceptor>
        <RouterProvider router={router} />
        <Toaster />
      </KycInterceptor>
    </AuthProvider>
  );
}

export default App;
