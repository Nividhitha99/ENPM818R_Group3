# Video Analytics Frontend - Modern UI Upgrade

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Docker (for containerized deployment)

### Local Development

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server:**
   ```bash
   npm start
   ```
   The app will open at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

### Docker Build

```bash
docker build -t video-analytics-frontend .
docker run -p 3000:80 video-analytics-frontend
```

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Sidebar.jsx
│   ├── Navbar.jsx
│   ├── UploadCard.jsx
│   ├── AnalyticsCard.jsx
│   ├── ProgressBar.jsx
│   └── Toast.jsx
├── charts/              # Chart components
│   ├── ViewsChart.jsx
│   ├── UploadsChart.jsx
│   └── VideoTypeChart.jsx
├── pages/                # Page components
│   ├── Dashboard.jsx
│   ├── Uploads.jsx
│   ├── Analytics.jsx
│   └── Settings.jsx
├── App.jsx              # Main app with routing
├── main.jsx             # Entry point
└── index.css            # TailwindCSS styles
```

## 🎨 Features

- ✅ Modern dashboard layout with sidebar navigation
- ✅ Drag-and-drop file upload with progress tracking
- ✅ Interactive charts (Line, Bar, Pie)
- ✅ Dark mode support
- ✅ Smooth animations with Framer Motion
- ✅ Responsive design
- ✅ Toast notifications
- ✅ Glassmorphism UI design

## 🔧 Technologies

- **React 18** - UI framework
- **TailwindCSS** - Styling
- **Framer Motion** - Animations
- **Recharts** - Data visualization
- **React Router** - Navigation
- **Heroicons** - Icons
- **Axios** - HTTP client

## 📡 API Endpoints

The frontend expects these endpoints (configured via nginx proxy):
- `/api/uploader/upload` - POST video upload
- `/api/analytics/stats` - GET analytics data

## 🎯 Routes

- `/dashboard` - Main dashboard (default)
- `/uploads` - Video upload page
- `/analytics` - Analytics and charts
- `/settings` - Settings page

