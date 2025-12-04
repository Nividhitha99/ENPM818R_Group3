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
  const [playingVideo, setPlayingVideo] = useState(null);

  useEffect(() => {
    fetchVideos();
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchVideos, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchVideos = async () => {
    try {
      const data = await analyticsAPI.getVideos(100, 'timestamp');
      setVideos(data.videos || []);
      // Debug: Log thumbnail URLs
      if (data.videos && data.videos.length > 0) {
        console.log('Videos with thumbnails:', data.videos.filter(v => v.thumbnail_url).map(v => ({
          id: v.video_id,
          thumbnail: v.thumbnail_url,
          status: v.status
        })));
      }
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
      // Find video and open in modal
      const video = videos.find(v => v.video_id === videoId);
      if (video) {
        setPlayingVideo(video);
      }
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

  // Get total count from API stats instead of just displayed videos
  const [totalVideoCount, setTotalVideoCount] = useState(0);
  
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const stats = await analyticsAPI.getStats();
        setTotalVideoCount(stats?.count || videos.length);
      } catch (err) {
        console.error('Failed to fetch stats', err);
        setTotalVideoCount(videos.length);
      }
    };
    if (!loading) {
      fetchStats();
    }
  }, [loading, videos.length]);
  
  const totalVideos = totalVideoCount || videos.length;
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
                <div className="flex items-center gap-4 flex-1">
                  {/* Thumbnail with Video Player */}
                  {video.status === 'PROCESSED' && video.processed_url ? (
                    <div className="flex-shrink-0">
                      {video.thumbnail_url ? (
                        <div className="relative group">
                          <img 
                            src={video.thumbnail_url} 
                            alt={video.filename || video.video_id}
                            className="w-32 h-20 object-cover rounded-lg cursor-pointer border border-gray-200 dark:border-gray-700"
                            onClick={() => {
                              setPlayingVideo(video);
                              handleView(video.video_id, video.processed_url);
                            }}
                            onError={(e) => {
                              // If thumbnail fails, show placeholder
                              e.target.style.display = 'none';
                              const parent = e.target.parentElement;
                              if (parent) {
                                parent.innerHTML = `
                                  <div class="w-32 h-20 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center cursor-pointer" onclick="window.handleThumbnailClick && window.handleThumbnailClick('${video.video_id}')">
                                    <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path>
                                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                    </svg>
                                  </div>
                                `;
                              }
                            }}
                          />
                          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-opacity rounded-lg pointer-events-none">
                            <PlayIcon className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                          </div>
                        </div>
                      ) : (
                        <div 
                          className="w-32 h-20 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center cursor-pointer hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                          onClick={() => {
                            setPlayingVideo(video);
                            handleView(video.video_id, video.processed_url);
                          }}
                        >
                          <PlayIcon className="w-8 h-8 text-gray-400" />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex-shrink-0 w-32 h-20 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                      <FilmIcon className="w-8 h-8 text-gray-400" />
                    </div>
                  )}
                  <div className="flex-1">
                    <p className="font-medium text-gray-800 dark:text-gray-200 mb-1">
                      {video.filename || video.video_id}
                    </p>
                    <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      <span>{formatFileSize(video.size)}</span>
                      {video.runtime > 0 && (
                        <>
                          <span>•</span>
                          <span>{Math.floor(video.runtime / 60)}:{(video.runtime % 60).toString().padStart(2, '0')}</span>
                        </>
                      )}
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

      {/* Video Player Modal */}
      {playingVideo && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setPlayingVideo(null)}
        >
          <div 
            className="bg-gray-900 rounded-lg max-w-4xl w-full p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-white text-lg font-semibold">
                {playingVideo.filename || playingVideo.video_id}
              </h3>
              <button
                onClick={() => setPlayingVideo(null)}
                className="text-white hover:text-gray-300 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <video 
              width="100%" 
              height="auto"
              className="rounded-lg"
              controls
              autoPlay
              src={playingVideo.processed_url}
            >
              <source src={playingVideo.processed_url} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;

