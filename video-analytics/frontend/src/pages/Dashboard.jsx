import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import AnalyticsCard from '../components/AnalyticsCard';
import { FilmIcon, EyeIcon, ClockIcon } from '@heroicons/react/24/outline';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const res = await axios.get('/api/analytics/stats');
      setStats(res.data);
    } catch (err) {
      console.error('Failed to fetch stats', err);
    } finally {
      setLoading(false);
    }
  };

  const totalVideos = stats?.count || 0;
  const totalViews = stats?.items?.reduce((sum, item) => sum + (item.views || 0), 0) || 0;
  const avgProcessingTime = '2.5s';

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-200 mb-2">
          Dashboard
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Overview of your video analytics
        </p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <AnalyticsCard
          title="Total Videos"
          value={loading ? '...' : totalVideos}
          icon={FilmIcon}
          color="indigo"
        />
        <AnalyticsCard
          title="Total Views"
          value={loading ? '...' : totalViews}
          icon={EyeIcon}
          color="green"
        />
        <AnalyticsCard
          title="Avg Processing"
          value={avgProcessingTime}
          icon={ClockIcon}
          color="purple"
        />
      </div>

      {stats && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card"
        >
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
            Recent Videos
          </h3>
          <div className="space-y-3">
            {stats.items?.slice(0, 5).map((item, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div>
                  <p className="font-medium text-gray-800 dark:text-gray-200">
                    {item.video_id}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {item.status} • {item.views || 0} views
                  </p>
                </div>
                <span className="px-3 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 rounded-full text-sm font-medium">
                  {item.status}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default Dashboard;

