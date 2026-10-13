import React, { type ReactNode } from 'react';

interface ModuleWrapperProps {
  title: string;
  children: ReactNode;
  icon?: string;
}

const ModuleWrapper: React.FC<ModuleWrapperProps> = ({ title, children, icon }) => {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
      <div className="p-6 border-b border-gray-700">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          {icon && <span>{icon}</span>}
          {title}
        </h3>
      </div>
      <div className="p-6">
        {children}
      </div>
    </div>
  );
};

export default ModuleWrapper;