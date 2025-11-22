import React from 'react';
import { motion } from 'framer-motion';

function ProgressBar({ progress, className = '' }) {
  return (
    <div className={`w-full ${className}`}>
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
          className="h-full bg-gradient-to-r from-indigo-500 to-blue-500 rounded-full"
        />
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 text-center">
        {Math.round(progress)}% uploaded
      </p>
    </div>
  );
}

export default ProgressBar;

