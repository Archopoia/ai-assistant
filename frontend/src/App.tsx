import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './services/auth';
import { Layout } from './components/common/Layout';
import { LoginForm } from './components/auth/LoginForm';
import { RegisterForm } from './components/auth/RegisterForm';
import { PasswordReset } from './components/auth/PasswordReset';
import { VerifyEmail } from './components/auth/VerifyEmail';
import { OAuthCallback } from './components/auth/OAuthCallback';
import { Dashboard } from './components/dashboard/Dashboard';
import { HealthProfileForm } from './components/profile/HealthProfileForm';
import { PrivacySettings } from './components/profile/PrivacySettings';
import { TwoFactorAuth } from './components/profile/TwoFactorAuth';
import { MealPlanPage } from './components/meal-plan/MealPlanPage';
import { RecipesPage } from './components/recipes/RecipesPage';
import { ShoppingListPage } from './components/shopping/ShoppingListPage';
import { ProgressChartsPage } from './components/progress/ProgressChartsPage';
import { AssistantPage } from './components/assistant/AssistantPage';

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div className="flex justify-center items-center h-screen">Loading...</div>;
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginForm />} />
      <Route path="/register" element={<RegisterForm />} />
      <Route path="/forgot-password" element={<PasswordReset />} />
      <Route path="/reset-password" element={<PasswordReset />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/auth/callback" element={<OAuthCallback />} />
      
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/meal-plan"
        element={
          <PrivateRoute>
            <Layout>
              <MealPlanPage />
            </Layout>
          </PrivateRoute>
        }
      />

      <Route
        path="/recipes"
        element={
          <PrivateRoute>
            <Layout>
              <RecipesPage />
            </Layout>
          </PrivateRoute>
        }
      />

      <Route
        path="/shopping-list"
        element={
          <PrivateRoute>
            <Layout>
              <ShoppingListPage />
            </Layout>
          </PrivateRoute>
        }
      />

      <Route
        path="/progress"
        element={
          <PrivateRoute>
            <Layout>
              <ProgressChartsPage />
            </Layout>
          </PrivateRoute>
        }
      />

      <Route
        path="/assistant"
        element={
          <PrivateRoute>
            <Layout>
              <AssistantPage />
            </Layout>
          </PrivateRoute>
        }
      />

      <Route
        path="/profile"
        element={
          <PrivateRoute>
            <Layout>
              <HealthProfileForm />
            </Layout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/privacy"
        element={
          <PrivateRoute>
            <Layout>
              <PrivacySettings />
            </Layout>
          </PrivateRoute>
        }
      />
      
      <Route
        path="/2fa"
        element={
          <PrivateRoute>
            <Layout>
              <TwoFactorAuth />
            </Layout>
          </PrivateRoute>
        }
      />
      
      <Route path="/" element={<Navigate to="/dashboard" />} />
    </Routes>
  );
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}

export default App;
