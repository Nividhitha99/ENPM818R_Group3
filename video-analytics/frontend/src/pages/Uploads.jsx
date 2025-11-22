import React from 'react';
import { motion } from 'framer-motion';
import UploadCard from '../components/UploadCard';

function Uploads() {
  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-200 mb-2">
          Upload Videos
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Upload and manage your video files
        </p>
      </motion.div>

      <UploadCard />
    </div>
  );
}

export default Uploads;

