#!/bin/bash
# CBS Research Demo Runner for Linux/macOS
# Requires Python 3.8+ with dependencies installed

echo "========================================="
echo "CBS Research Demo Suite - 1 Gbps Network"
echo "========================================="
echo

function show_menu() {
    echo "Select demo option:"
    echo "1. Generate all visualizations"
    echo "2. Run interactive Streamlit demo"
    echo "3. Start Docker demo environment"
    echo "4. Run performance benchmark"
    echo "5. Generate ML optimization report"
    echo "6. Launch Jupyter notebook"
    echo "7. Exit"
    echo
    read -p "Enter your choice (1-7): " choice
}

function generate_viz() {
    echo
    echo "Generating visualizations..."
    python3 video_demo_script.py
    echo "Press any key to continue..."
    read -n 1
}

function run_streamlit() {
    echo
    echo "Starting Streamlit demo..."
    cd demo_output
    streamlit run streamlit_demo.py --server.port 8501
    cd ..
}

function start_docker() {
    echo
    echo "Starting Docker environment..."
    cd ..
    docker-compose up demo
}

function run_benchmark() {
    echo
    echo "Running performance benchmark..."
    cd ..
    python3 -m src.performance_benchmark --iterations 10 --output results/
    echo "Press any key to continue..."
    read -n 1
}

function generate_ml_report() {
    echo
    echo "Generating ML optimization report..."
    cd ..
    python3 -m src.ml_optimizer --analyze --output results/ml_analysis.html
    echo "Press any key to continue..."
    read -n 1
}

function launch_jupyter() {
    echo
    echo "Launching Jupyter notebook..."
    cd ..
    jupyter lab --port=8888
}

# Main loop
while true; do
    show_menu
    case $choice in
        1) generate_viz ;;
        2) run_streamlit ;;
        3) start_docker ;;
        4) run_benchmark ;;
        5) generate_ml_report ;;
        6) launch_jupyter ;;
        7) echo; echo "Thank you for using CBS Research Demo!"; exit 0 ;;
        *) echo "Invalid option. Please try again." ;;
    esac
done