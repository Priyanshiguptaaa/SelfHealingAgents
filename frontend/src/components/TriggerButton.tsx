import React, { useState } from 'react';
import { Play, Zap } from 'lucide-react';

interface TriggerButtonProps {
  onTrigger: () => Promise<void>;
  variant?: 'primary' | 'secondary';
}

const TriggerButton: React.FC<TriggerButtonProps> = ({ onTrigger, variant = 'secondary' }) => {
  const [isTriggering, setIsTriggering] = useState(false);

  const handleClick = async () => {
    setIsTriggering(true);
    try {
      await onTrigger();
    } finally {
      setIsTriggering(false);
    }
  };

  const baseClasses = "inline-flex items-center px-4 py-2 border rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2";
  const variantClasses = variant === 'primary' 
    ? "border-transparent bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500"
    : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50 focus:ring-primary-500";

  return (
    <button
      onClick={handleClick}
      disabled={isTriggering}
      className={`${baseClasses} ${variantClasses} ${isTriggering ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {isTriggering ? (
        <>
          <Zap className="h-4 w-4 mr-2 animate-pulse" />
          Triggering...
        </>
      ) : (
        <>
          <Play className="h-4 w-4 mr-2" />
          Trigger Failure
        </>
      )}
    </button>
  );
};

export default TriggerButton; 