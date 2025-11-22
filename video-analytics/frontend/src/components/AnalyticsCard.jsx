import React from 'react';
import { motion } from 'framer-motion';

function AnalyticsCard({ title, value, icon: Icon, color = 'indigo' }) {
  const colorClasses = {
    indigo: 'from-indigo-500 to-blue-500',
    green: 'from-green-500 to-emerald-500',
    purple: 'from-purple-500 to-pink-500',
    orange: 'from-orange-500 to-red-500',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.05 }}
      className={`card bg-gradient-to-br ${colorClasses[color]} text-white`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-white/80 text-sm mb-1">{title}</p>
          <p className="text-3xl font-bold">{value}</p>
        </div>
        {Icon && (
          <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default AnalyticsCard;

