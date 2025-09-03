@echo off
REM Paper Compilation Script for Windows
REM Compiles LaTeX papers to PDF

echo ====================================
echo CBS TSN Research Paper Compilation
echo ====================================
echo.

REM Check if pdflatex is installed
where pdflatex >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pdflatex not found. Please install MiKTeX or TeX Live.
    echo Download from: https://miktex.org/download
    pause
    exit /b 1
)

REM Create output directory
if not exist "pdf" mkdir pdf

REM Compile English paper
echo [1/2] Compiling English paper...
pdflatex -output-directory=pdf -interaction=nonstopmode paper_english_final.tex >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] English paper compiled successfully
    pdflatex -output-directory=pdf -interaction=nonstopmode paper_english_final.tex >nul 2>&1
    echo [OK] Second pass completed
) else (
    echo [ERROR] Failed to compile English paper
)

REM Compile Korean paper
echo [2/2] Compiling Korean paper...
pdflatex -output-directory=pdf -interaction=nonstopmode paper_korean_final.tex >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Korean paper compiled successfully
    pdflatex -output-directory=pdf -interaction=nonstopmode paper_korean_final.tex >nul 2>&1
    echo [OK] Second pass completed
) else (
    echo [ERROR] Failed to compile Korean paper
)

echo.
echo ====================================
echo Compilation complete!
echo PDFs are in the 'pdf' directory
echo ====================================
pause