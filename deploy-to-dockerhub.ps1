# Docker Hub Deployment Script for Dolder Parking App (PowerShell)
# Replace 'yourusername' with your actual Docker Hub username

$DOCKER_USERNAME = "sarmadaslam"
$IMAGE_NAME = "dolder-parking"
$TAG = "latest"

Write-Host "🐳 Building Docker image for Dolder Parking..." -ForegroundColor Cyan
docker build -f Dockerfile.prod -t "$DOCKER_USERNAME/$IMAGE_NAME`:$TAG" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed! Please check your Dockerfile." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "📝 Tagging image..." -ForegroundColor Cyan
docker tag "$DOCKER_USERNAME/$IMAGE_NAME`:$TAG" "$DOCKER_USERNAME/$IMAGE_NAME`:latest"

Write-Host "🔐 Logging into Docker Hub..." -ForegroundColor Cyan
docker login

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Login failed! Please check your credentials." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "⬆️ Pushing to Docker Hub..." -ForegroundColor Cyan
docker push "$DOCKER_USERNAME/$IMAGE_NAME`:$TAG"
docker push "$DOCKER_USERNAME/$IMAGE_NAME`:latest"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Push failed! Please check your internet connection and Docker Hub permissions." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Successfully deployed to Docker Hub!" -ForegroundColor Green
Write-Host "📋 Your image is now available at: docker.io/$DOCKER_USERNAME/$IMAGE_NAME" -ForegroundColor Yellow
Write-Host ""
Write-Host "🚀 To run on any server:" -ForegroundColor Cyan
Write-Host "docker run -d -p 8000:8000 $DOCKER_USERNAME/$IMAGE_NAME" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Or with docker-compose:" -ForegroundColor Cyan
Write-Host "docker-compose -f docker-compose.prod.yml up -d" -ForegroundColor White
Write-Host ""
Write-Host "🎯 Next step: Deploy to Railway or Render for a live URL!" -ForegroundColor Magenta
Read-Host "Press Enter to exit"
