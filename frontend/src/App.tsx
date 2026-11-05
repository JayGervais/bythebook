import { Route, Routes } from 'react-router-dom';
import { RequireAuth } from './auth';
import { AccountPage, PrivacyPage } from './pages/AccountPage';
import { Login, Register } from './pages/AuthPages';
import { HomePage } from './pages/HomePage';
import { InspectionPage } from './pages/InspectionPage';
import { InvitePage } from './pages/InvitePage';
import { JoinPage } from './pages/JoinPage';
import { Landing } from './pages/Landing';
import { PropertyPage } from './pages/PropertyPage';
import { NewTenancy, TenancyDetail } from './pages/TenancyPage';
import { TenantHome } from './pages/TenantHome';
import { useAuth } from './auth';

function HomeGate() {
  const { user } = useAuth();
  return user?.role === 'tenant' ? <TenantHome /> : <HomePage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/invite/:token" element={<InvitePage />} />
      <Route path="/join/:token" element={<JoinPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/home" element={<HomeGate />} />
        <Route path="/property" element={<PropertyPage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="/tenancies/new" element={<NewTenancy />} />
        <Route path="/tenancies/:id" element={<TenancyDetail />} />
        <Route path="/inspections/:id" element={<InspectionPage />} />
      </Route>
    </Routes>
  );
}
