@echo off
REM CBS Research Demo Runner for Windows
REM Requires Python 3.8+ with dependencies installed

echo =========================================
echo CBS Research Demo Suite - 1 Gbps Network
echo =========================================
echo.

:menu
echo Select demo option:
echo 1. Generate all visualizations
echo 2. Run interactive Streamlit demo
echo 3. Start Docker demo environment
echo 4. Run performance benchmark
echo 5. Generate ML optimization report
echo 6. Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto generate_viz
if "%choice%"=="2" goto streamlit
if "%choice%"=="3" goto docker
if "%choice%"=="4" goto benchmark
if "%choice%"=="5" goto ml_report
if "%choice%"=="6" goto end

:generate_viz
echo.
echo Generating visualizations...
python video_demo_script.py
pause
goto menu

:streamlit
echo.
echo Starting Streamlit demo...
cd demo_output
streamlit run streamlit_demo.py --server.port 8501
pause
goto menu

:docker
echo.
echo Starting Docker environment...
cd ..
docker-compose up demo
pause
goto menu

:benchmark
echo.
echo Running performance benchmark...
cd ..
python -m src.performance_benchmark --iterations 10 --output results/
pause
goto menu

:ml_report
echo.
echo Generating ML optimization report...
cd ..
python -m src.ml_optimizer --analyze --output results/ml_analysis.html
pause
goto menu

:end
echo.
echo Thank you for using CBS Research Demo!
exit /b 0