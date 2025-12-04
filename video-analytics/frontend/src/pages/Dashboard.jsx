import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import AnalyticsCard from '../components/AnalyticsCard';
import { analyticsAPI } from '../services/api';
import { FilmIcon, EyeIcon, PlayIcon, HeartIcon } from '@heroicons/react/24/outline';
import { HeartIcon as HeartSolidIcon } from '@heroicons/react/24/solid';

function Dashboard() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState({});

  useEffect(() => {
    fetchVideos();
    const interval = setInterval(fetchVideos, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchVideos = async () => {
    try {
      const data = await analyticsAPI.getVideos(10, 'timestamp');
      setVideos(data.videos || []);
    } catch (err) {
      console.error('Failed to fetch videos', err);
    } finally {
      setLoading(false);
    }
  };

  const handleView = async (videoId, processedUrl) => {
    try {
      setUpdating(prev => ({ ...prev, [videoId]: 'viewing' }));
      await analyticsAPI.recordView(videoId);
      // Open video in new tab
      window.open(processedUrl, '_blank');
      // Refresh video list to update view count
      await fetchVideos();
    } catch (err) {
      console.error('Failed to record view', err);
    } finally {
      setUpdating(prev => {
        const newState = { ...prev };
        delete newState[videoId];
        return newState;
      });
    }
  };

  const handleLike = async (videoId) => {
    try {
      setUpdating(prev => ({ ...prev, [videoId]: 'liking' }));
      await analyticsAPI.recordLike(videoId);
      // Update local state immediately for better UX
      setVideos(prevVideos =>
        prevVideos.map(video =>
          video.video_id === videoId
            ? { ...video, likes: (video.likes || 0) + 1 }
            : video
        )
      );
    } catch (err) {
      console.error('Failed to record like', err);
    } finally {
      setUpdating(prev => {
        const newState = { ...prev };
        delete newState[videoId];
        return newState;
      });
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const totalVideos = videos.length;
  const totalViews = videos.reduce((sum, video) => sum + (video.views || 0), 0);
  const totalLikes = videos.reduce((sum, video) => sum + (video.likes || 0), 0);

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
          title="Total Likes"
          value={loading ? '...' : totalLikes}
          icon={HeartIcon}
          color="red"
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card"
      >
        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
          Recent Videos
        </h3>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : videos.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 text-center py-8">
            No videos uploaded yet
          </p>
        ) : (
          <div className="space-y-3">
            {videos.map((video, idx) => (
              <motion.div
                key={video.video_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <div className="flex-1">
                  <p className="font-medium text-gray-800 dark:text-gray-200 mb-1">
                    {video.filename || video.video_id}
                  </p>
                  <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                    <span>{formatFileSize(video.size)}</span>
                    <span>•</span>
                    <span>{video.views || 0} views</span>
                    <span>•</span>
                    <span>{video.likes || 0} likes</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      video.status === 'PROCESSED' 
                        ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                        : 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300'
                    }`}>
                      {video.status}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleView(video.video_id, video.processed_url)}
                    disabled={updating[video.video_id] === 'viewing' || video.status !== 'PROCESSED'}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <PlayIcon className="w-4 h-4" />
                    View Video
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => handleLike(video.video_id)}
                    disabled={updating[video.video_id] === 'liking'}
                    className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {video.likes > 0 ? (
                      <HeartSolidIcon className="w-4 h-4" />
                    ) : (
                      <HeartIcon className="w-4 h-4" />
                    )}
                    {video.likes || 0}
                  </motion.button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}

export default Dashboard;

