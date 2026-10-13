import React, { Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import UsersPage from './pages/UsersPage';
import UserPermissionsPage from './pages/UserPermissionsPage';

const UsersModule: React.FC = () => (
  <div className="h-full">
    <Suspense fallback={<div className="flex items-center justify-center h-full text-gray-400">Cargando...</div>}>
      <Routes>
        <Route index element={<UsersPage />} />
        <Route path=":userId/permissions" element={<UserPermissionsPage />} />
      </Routes>
    </Suspense>
  </div>
);

export default UsersModule;
