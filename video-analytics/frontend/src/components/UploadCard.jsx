import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CloudArrowUpIcon, XMarkIcon } from '@heroicons/react/24/outline';
import ProgressBar from './ProgressBar';
import Toast from './Toast';
import axios from 'axios';
import { analyticsAPI } from '../services/api';

function UploadCard() {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadedVideoId, setUploadedVideoId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [toast, setToast] = useState(null);
  const fileInputRef = useRef(null);
  const progressIntervalRef = useRef(null);
  const processingPollRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  // Poll for video processing status
  useEffect(() => {
    if (processing) {
      let pollCount = 0;
      const maxPolls = 60; // Max 2 minutes (60 * 2 seconds)
      
      const checkProcessing = async () => {
        try {
          pollCount++;
          
          // If we have video_id, check specific video
          if (uploadedVideoId) {
            const data = await analyticsAPI.getVideos(1000, 'timestamp');
            const video = data.videos.find(v => v.video_id === uploadedVideoId);
            
            if (video && video.status === 'PROCESSED') {
              // Video is processed, stop polling
              setProcessing(false);
              setUploadedVideoId(null);
              if (processingPollRef.current) {
                clearInterval(processingPollRef.current);
                processingPollRef.current = null;
              }
              setToast({ type: 'success', message: 'Video processed! Thumbnail generated.' });
              return;
            }
          } else {
            // No video_id, check for newest video that's processed
            const data = await analyticsAPI.getVideos(10, 'timestamp');
            const newestVideo = data.videos[0];
            
            if (newestVideo && newestVideo.status === 'PROCESSED') {
              // Assume this is our video if it was just processed
              setProcessing(false);
              setUploadedVideoId(null);
              if (processingPollRef.current) {
                clearInterval(processingPollRef.current);
                processingPollRef.current = null;
              }
              setToast({ type: 'success', message: 'Video processed! Thumbnail generated.' });
              return;
            }
          }
          
          // Stop polling after max attempts
          if (pollCount >= maxPolls) {
            setProcessing(false);
            setUploadedVideoId(null);
            if (processingPollRef.current) {
              clearInterval(processingPollRef.current);
              processingPollRef.current = null;
            }
            setToast({ type: 'warning', message: 'Processing is taking longer than expected. Please refresh.' });
          }
        } catch (err) {
          console.error('Error checking processing status:', err);
        }
      };

      // Poll every 2 seconds
      processingPollRef.current = setInterval(checkProcessing, 2000);
      
      return () => {
        if (processingPollRef.current) {
          clearInterval(processingPollRef.current);
          processingPollRef.current = null;
        }
      };
    }
  }, [processing, uploadedVideoId]);

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploading(true);
      setProgress(0);

      const response = await axios.post('/api/uploader/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 600000, // 10 minutes timeout for large files
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setProgress(percentCompleted);
          }
        },
      });

      // Upload complete, extract video_id from response
      const videoId = response.data?.video_id || response.data?.id || response.data?.file_id;
      
      setUploading(false);
      setProcessing(true);
      
      if (videoId) {
        setUploadedVideoId(videoId);
        setToast({ type: 'success', message: 'Upload successful! Processing...' });
      } else {
        // Fallback: poll all videos to find the newest one
        setToast({ type: 'success', message: 'Upload successful! Processing...' });
        // Will check in polling
      }
      
      setFile(null);
    } catch (err) {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      if (processingPollRef.current) {
        clearInterval(processingPollRef.current);
      }
      setToast({ type: 'error', message: 'Upload failed. Please try again.' });
      setUploading(false);
      setProcessing(false);
      setProgress(0);
      setUploadedVideoId(null);
    }
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card"
      >
        <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-4">
          Upload Video
        </h3>
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
            isDragging
              ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-indigo-400 dark:hover:border-indigo-500'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            accept="video/*"
            className="hidden"
          />
          <CloudArrowUpIcon className="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500" />
          <p className="text-gray-600 dark:text-gray-400 mb-2">
            Drag and drop a video file here, or click to select
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-500">
            Supports MP4, MOV, AVI, and more
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-1 font-medium">
            Upload videos &lt; 500 MB
          </p>
        </div>

        {file && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900 rounded flex items-center justify-center">
                <span className="text-indigo-600 dark:text-indigo-400 font-semibold">
                  {file.name.split('.').pop().toUpperCase()}
                </span>
              </div>
              <div>
                <p className="font-medium text-gray-800 dark:text-gray-200">
                  {file.name}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </motion.div>
        )}

        {uploading && (
          <div className="mt-4">
            <ProgressBar progress={progress} className="mb-2" />
            <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
              Uploading... {progress}%
            </p>
          </div>
        )}
        
        {processing && !uploading && (
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-blue-500"></div>
              <p className="text-sm text-blue-700 dark:text-blue-300 font-medium">
                Processing... Generating Thumbnail...
              </p>
            </div>
          </div>
        )}

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleUpload}
          disabled={!file || uploading}
          className="mt-6 w-full bg-gradient-to-r from-indigo-500 to-blue-500 text-white py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {uploading ? 'Uploading...' : 'Upload Video'}
        </motion.button>
      </motion.div>

      <AnimatePresence>
        {toast && (
          <Toast
            type={toast.type}
            message={toast.message}
            onClose={() => setToast(null)}
          />
        )}
      </AnimatePresence>
    </>
  );
}

export default UploadCard;

