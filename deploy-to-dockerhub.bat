@echo off
REM Docker Hub Deployment Script for Dolder Parking App (Windows)
REM Replace 'yourusername' with your actual Docker Hub username

set DOCKER_USERNAME=sarmadaslam
set IMAGE_NAME=dolder-parking
set TAG=latest

echo 🐳 Building Docker image for Dolder Parking...
docker build -f Dockerfile.prod -t %DOCKER_USERNAME%/%IMAGE_NAME%:%TAG% .

if %errorlevel% neq 0 (
    echo ❌ Build failed! Please check your Dockerfile.
    pause
    exit /b 1
)

echo 📝 Tagging image...
docker tag %DOCKER_USERNAME%/%IMAGE_NAME%:%TAG% %DOCKER_USERNAME%/%IMAGE_NAME%:latest

echo 🔐 Logging into Docker Hub...
docker login

if %errorlevel% neq 0 (
    echo ❌ Login failed! Please check your credentials.
    pause
    exit /b 1
)

echo ⬆️ Pushing to Docker Hub...
docker push %DOCKER_USERNAME%/%IMAGE_NAME%:%TAG%
docker push %DOCKER_USERNAME%/%IMAGE_NAME%:latest

if %errorlevel% neq 0 (
    echo ❌ Push failed! Please check your internet connection and Docker Hub permissions.
    pause
    exit /b 1
)

echo ✅ Successfully deployed to Docker Hub!
echo 📋 Your image is now available at: docker.io/%DOCKER_USERNAME%/%IMAGE_NAME%
echo.
echo 🚀 To run on any server:
echo docker run -d -p 8000:8000 %DOCKER_USERNAME%/%IMAGE_NAME%
echo.
echo 🌐 Or with docker-compose:
echo docker-compose -f docker-compose.prod.yml up -d
echo.
echo 🎯 Next step: Deploy to Railway or Render for a live URL!
pause
