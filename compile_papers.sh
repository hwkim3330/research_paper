#!/bin/bash

# Paper Compilation Script for Linux/Mac
# Compiles LaTeX papers to PDF

echo "===================================="
echo "CBS TSN Research Paper Compilation"
echo "===================================="
echo

# Check if pdflatex is installed
if ! command -v pdflatex &> /dev/null; then
    echo "ERROR: pdflatex not found. Please install TeX Live or MacTeX."
    echo "Ubuntu/Debian: sudo apt-get install texlive-full"
    echo "Mac: brew install --cask mactex"
    exit 1
fi

# Create output directory
mkdir -p pdf

# Function to compile paper
compile_paper() {
    local tex_file=$1
    local paper_name=$2
    
    echo "[$paper_name] Compiling..."
    
    # First pass
    if pdflatex -output-directory=pdf -interaction=nonstopmode "$tex_file" > /dev/null 2>&1; then
        echo "[$paper_name] First pass successful"
        
        # Second pass for references
        if pdflatex -output-directory=pdf -interaction=nonstopmode "$tex_file" > /dev/null 2>&1; then
            echo "[$paper_name] Second pass successful ✓"
            return 0
        fi
    fi
    
    echo "[$paper_name] Compilation failed ✗"
    return 1
}

# Compile papers
echo "[1/2] Compiling English paper..."
compile_paper "paper_english_final.tex" "English"

echo "[2/2] Compiling Korean paper..."
compile_paper "paper_korean_final.tex" "Korean"

echo
echo "===================================="
echo "Compilation complete!"
echo "PDFs are in the 'pdf' directory"
echo "===================================="

# List generated PDFs
echo
echo "Generated files:"
ls -lh pdf/*.pdf 2>/dev/null || echo "No PDFs generated"