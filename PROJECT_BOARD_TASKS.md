# Project Board Tasks - ENPM818R Group 3

## 📋 Backlog
*(Future work identified but not yet ready to start)*

### Frontend (@hdharani-sec)
- [ ] Implement video player component with playback controls
- [ ] Add video search and filtering functionality
- [ ] Implement user profile page and settings
- [ ] Add dark mode toggle UI component
- [ ] Create responsive mobile layout for all pages
- [ ] Add loading skeletons for better UX
- [ ] Implement error boundary components
- [ ] Add unit tests for React components

### Uploader Service (@s-mahima09)
- [ ] Implement chunked/multipart upload for large files (>500MB)
- [ ] Add upload progress tracking API endpoint
- [ ] Implement upload retry mechanism
- [ ] Add support for batch video uploads
- [ ] Create upload queue management UI
- [ ] Add video preview before upload confirmation

### Processor Service (@joyson13)
- [ ] Implement multiple video quality transcoding (360p, 720p, 1080p)
- [ ] Add video format conversion options (MP4, WebM, HLS)
- [ ] Implement parallel processing for multiple videos
- [ ] Add processing progress tracking and status updates
- [ ] Implement video compression optimization
- [ ] Add support for video metadata extraction (duration, resolution, codec)
- [ ] Create dead letter queue handling for failed processing jobs

### Analytics Service (@joyson13)
- [ ] Implement advanced analytics filters (date range, video type)
- [ ] Add export functionality for analytics data (CSV, JSON)
- [ ] Implement real-time analytics updates via WebSocket
- [ ] Add video engagement heatmaps
- [ ] Create custom analytics dashboard widgets
- [ ] Implement analytics caching layer (Redis)

### Auth Service
- [ ] Implement user registration endpoint
- [ ] Add password reset functionality
- [ ] Implement role-based access control (RBAC)
- [ ] Add OAuth2 social login integration
- [ ] Implement session management
- [ ] Add user profile management endpoints

### Gateway Service
- [ ] Implement rate limiting per user/IP
- [ ] Add request caching for analytics endpoints
- [ ] Implement circuit breaker pattern
- [ ] Add API versioning support
- [ ] Create API documentation (OpenAPI/Swagger)
- [ ] Implement request/response transformation

### Infrastructure/Terraform (@danitrical)
- [ ] Add CloudFront CDN for video delivery
- [ ] Implement S3 lifecycle policies for video archival
- [ ] Add RDS database for user data (if needed)
- [ ] Create staging environment infrastructure
- [ ] Implement backup and disaster recovery strategy
- [ ] Add VPC endpoints for AWS services
- [ ] Create separate Terraform modules for each component

### DevOps & App Building (@Nivedhitha99)
- [ ] Set up Kubernetes Horizontal Pod Autoscaler (HPA)
- [ ] Implement blue-green deployment strategy
- [ ] Add Kubernetes resource quotas and limits
- [ ] Create Helm charts for easier deployment
- [ ] Implement service mesh (Istio/Linkerd) for observability
- [ ] Add pod disruption budgets for high availability
- [ ] Create development environment setup scripts

### CI/CD (@nkafridi1)
- [ ] Add automated testing to CI pipeline
- [ ] Implement automated security scanning (Trivy) in pipeline
- [ ] Add code quality checks (SonarQube/CodeClimate)
- [ ] Implement automated deployment to staging
- [ ] Add rollback automation
- [ ] Create deployment notifications (Slack/Email)
- [ ] Implement feature flags for gradual rollouts

### Observability & Monitoring (@steward)
- [ ] Set up Prometheus metrics collection
- [ ] Create Grafana dashboards for all services
- [ ] Implement distributed tracing (Jaeger/Tempo)
- [ ] Add custom CloudWatch alarms
- [ ] Create runbooks for common issues
- [ ] Implement log aggregation and analysis
- [ ] Add APM (Application Performance Monitoring)

### Documentation
- [ ] Create API documentation with examples
- [ ] Write deployment runbook
- [ ] Create troubleshooting guide
- [ ] Document local development setup
- [ ] Create architecture decision records (ADRs)
- [ ] Write user guide for video uploads

---

## ✅ Ready
*(Well-defined tasks ready to be picked up)*

### Documentation Fixes
- [ ] Fix incomplete sentence in CONTRIBUTING.md ("Create a branch f" → "Create a branch from main")
- [ ] Update CONTRIBUTING.md with correct branch naming convention (member-number-feature)
- [ ] Add missing sections to CONTRIBUTING.md (testing requirements details)

### Frontend (@hdharani-sec)
- [ ] Fix any frontend security vulnerabilities from Trivy scan
- [ ] Add error handling for API failures
- [ ] Implement proper loading states for all API calls
- [ ] Add form validation for video upload

### Uploader Service (@s-mahima09)
- [ ] Add comprehensive error handling for S3 upload failures
- [ ] Implement proper file type validation
- [ ] Add unit tests for upload validation logic
- [ ] Document upload API endpoints

### Processor Service (@joyson13)
- [ ] Add error handling for FFmpeg failures
- [ ] Implement proper cleanup of temporary files
- [ ] Add processing status tracking
- [ ] Create unit tests for video processing functions

### Analytics Service (@joyson13)
- [ ] Add error handling for S3 metadata retrieval failures
- [ ] Implement pagination for video list endpoint
- [ ] Add sorting options (date, views, likes)
- [ ] Create unit tests for analytics calculations

### Gateway Service
- [ ] Add authentication middleware integration
- [ ] Implement proper error response formatting
- [ ] Add request validation
- [ ] Create unit tests for routing logic

### Auth Service
- [ ] Implement JWT token refresh endpoint
- [ ] Add password hashing validation
- [ ] Create user authentication tests
- [ ] Document authentication flow

### Infrastructure (@danitrical)
- [ ] Configure ACM certificate in ingress.yaml (uncomment and set ARN)
- [ ] Verify all Terraform resources are properly tagged
- [ ] Add Terraform state locking
- [ ] Document infrastructure setup process

### CI/CD (@nkafridi1)
- [ ] Add Trivy security scanning to CI pipeline
- [ ] Implement automated testing in GitHub Actions
- [ ] Add build status badges to README
- [ ] Create deployment workflow for staging environment

### Observability (@steward)
- [ ] Verify all services are logging to CloudWatch
- [ ] Set up basic CloudWatch alarms
- [ ] Create initial monitoring dashboard
- [ ] Document logging standards

---

## 🔄 In Progress
*(Tasks currently being worked on)*

### Security Review
- [ ] Review and merge security changes PR (#16)
- [ ] Audit IAM roles and policies
- [ ] Review network security policies
- [ ] Verify all secrets are properly managed

### Testing
- [ ] Write unit tests for uploader service
- [ ] Write unit tests for processor service
- [ ] Write unit tests for analytics service
- [ ] Write unit tests for gateway service
- [ ] Write unit tests for auth service
- [ ] Create integration test suite

### Code Quality
- [ ] Fix linting errors across all services
- [ ] Add type hints to all Python functions
- [ ] Standardize error handling patterns
- [ ] Review and refactor code for best practices

---

## 👀 In Review
*(Completed tasks awaiting review)*

### Security
- [ ] PR: Added security changes to be reviewed (#16) - *Currently in backlog, move to In Review*

### Documentation
- [ ] PR: Fix CONTRIBUTING.md incomplete sentence
- [ ] PR: Update CODEOWNERS with team assignments

### Infrastructure
- [ ] PR: Terraform infrastructure setup
- [ ] PR: Kubernetes manifests for all services

### Services
- [ ] PR: Uploader service implementation
- [ ] PR: Processor service implementation
- [ ] PR: Analytics service implementation
- [ ] PR: Gateway service implementation
- [ ] PR: Auth service implementation
- [ ] PR: Frontend service implementation

---

## ✅ Done
*(Completed and merged tasks)*

### Project Setup
- [x] Created PULL_REQUEST_TEMPLATE.md
- [x] Created CODEOWNERS file
- [x] Created CONTRIBUTING.md
- [x] Created ISSUE_TEMPLATE/task.md
- [x] Set up GitHub Project Board
- [x] Initial repository structure

### Infrastructure
- [x] Basic Terraform setup for EKS cluster
- [x] VPC and networking configuration
- [x] EKS cluster creation
- [x] IRSA (IAM Roles for Service Accounts) setup

### Services - Initial Implementation
- [x] Uploader service basic implementation
- [x] Processor service basic implementation
- [x] Analytics service basic implementation
- [x] Gateway service basic implementation
- [x] Auth service basic implementation
- [x] Frontend service basic implementation

### CI/CD
- [x] GitHub Actions workflow for build and push to ECR
- [x] Docker image builds for all services

### Documentation
- [x] SYSTEM_ARCHITECTURE.md
- [x] EXECUTIVE_SUMMARY.md
- [x] DEPLOYMENT.md
- [x] TESTING_GUIDE.md

---

## 📝 Notes

### Priority Guidelines
1. **High Priority**: Security fixes, critical bugs, blocking issues
2. **Medium Priority**: Feature enhancements, performance improvements
3. **Low Priority**: Nice-to-have features, documentation improvements

### Task Assignment
- Assign tasks based on CODEOWNERS file
- Use branch naming: `member-number-feature-name`
- Link PRs to related issues
- Update project board when moving tasks between columns

### Definition of Done
- [ ] Code reviewed and approved
- [ ] All tests passing
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Deployed to staging (if applicable)
- [ ] PR merged to main
