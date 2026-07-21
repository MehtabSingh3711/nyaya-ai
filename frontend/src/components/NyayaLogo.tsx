import React from 'react';
import logoDark from '../../assets/nyayaai-logo-dark.png';
import logoLight from '../../assets/nyayaai-logo-light.png';

interface LogoProps {
  className?: string;
  height?: number;
}

export default function NyayaLogo({ className = '', height = 32 }: LogoProps) {
  return (
    <div className={`relative inline-block ${className}`} style={{ height }}>
      {/* Light theme logo (shown when NOT in dark mode) */}
      <img
        src={logoLight.src}
        alt="Nyaya AI Logo"
        className="block dark:hidden object-contain"
        style={{ height: '100%', width: 'auto' }}
      />
      {/* Dark theme logo (shown when in dark mode) */}
      <img
        src={logoDark.src}
        alt="Nyaya AI Logo"
        className="hidden dark:block object-contain"
        style={{ height: '100%', width: 'auto' }}
      />
    </div>
  );
}
