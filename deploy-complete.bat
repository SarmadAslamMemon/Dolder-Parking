@echo off
REM Complete Docker Deployment Script (SQLite version)
REM This creates a single image with everything included

set DOCKER_USERNAME=sarmadaslam
set IMAGE_NAME=dolder-parking-complete
set TAG=latest

echo 🐳 Building Complete Docker image with SQLite...
docker build -f Dockerfile.complete -t %DOCKER_USERNAME%/%IMAGE_NAME%:%TAG% .

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

echo ✅ Successfully deployed complete image to Docker Hub!
echo 📋 Your complete image: docker.io/%DOCKER_USERNAME%/%IMAGE_NAME%
echo.
echo 🚀 To run locally:
echo docker run -d -p 8000:8000 %DOCKER_USERNAME%/%IMAGE_NAME%
echo.
echo 🎯 Deploy to Railway with this image:
echo Image: %DOCKER_USERNAME%/%IMAGE_NAME%
echo Port: 8000
echo Environment Variables: None needed! (Uses SQLite)
echo.
echo 🔑 Default Login:
echo Username: admin
echo Password: admin
echo.
pause

