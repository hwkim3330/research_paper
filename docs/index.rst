CBS Research Project Documentation
====================================

Welcome to the Credit-Based Shaper (CBS) Research Project documentation. This project provides a comprehensive implementation and analysis toolkit for IEEE 802.1Qav Credit-Based Shaper mechanisms in automotive Time-Sensitive Networking (TSN).

.. image:: https://img.shields.io/badge/IEEE-802.1Qav-blue
   :alt: IEEE 802.1Qav

.. image:: https://img.shields.io/badge/TSN-Automotive-green
   :alt: TSN Automotive

.. image:: https://img.shields.io/badge/Python-3.8%2B-blue
   :alt: Python 3.8+

Project Overview
----------------

The CBS Research Project is a comprehensive suite of tools and analysis scripts for:

* **CBS Parameter Calculation**: Advanced algorithms for computing optimal CBS parameters
* **Performance Analysis**: Detailed analysis tools for CBS implementation effectiveness  
* **Traffic Generation**: Realistic automotive network traffic simulation
* **Benchmarking**: Performance measurement and regression testing
* **Visualization**: Interactive data analysis and result presentation

Key Features
------------

✅ **Production-Ready CBS Calculator**
   - Multi-stream parameter optimization
   - Real-time validation and warnings
   - Export to industry-standard formats (YAML, CSV)

✅ **Comprehensive Testing Framework**
   - Unit tests with 80%+ coverage
   - Integration tests for end-to-end validation
   - Performance regression testing

✅ **Advanced Data Analysis**
   - Interactive visualizations with Plotly
   - Statistical analysis and reporting
   - Performance trend monitoring

✅ **Realistic Traffic Generation**
   - Automotive-specific traffic profiles
   - Multi-scenario simulation capabilities
   - Network performance testing

✅ **CI/CD Pipeline**
   - Automated testing and quality checks
   - Performance monitoring and alerts
   - Documentation generation

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/your-org/cbs-research.git
   cd cbs-research
   pip install -r requirements.txt

Basic Usage
~~~~~~~~~~~

Calculate CBS parameters for an autonomous vehicle scenario:

.. code-block:: python

   from src.cbs_calculator import CBSCalculator, StreamConfig, TrafficType

   # Create calculator
   calculator = CBSCalculator(link_speed_mbps=1000)

   # Define video stream
   video_stream = StreamConfig(
       name="Front_Camera_4K",
       traffic_type=TrafficType.VIDEO_4K,
       bitrate_mbps=25.0,
       fps=60,
       resolution="3840x2160", 
       priority=6,
       max_latency_ms=20.0,
       max_jitter_ms=3.0
   )

   # Calculate CBS parameters
   params = calculator.calculate_cbs_params(video_stream)
   print(f"idleSlope: {params.idle_slope} bps")
   print(f"Efficiency: {params.efficiency_percent:.1f}%")

Run Data Analysis
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python src/data_analyzer.py --data results/experiment_data.json

Generate Performance Report
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python src/performance_benchmark.py --test all --output-dir benchmark_results

Research Results
----------------

Our implementation achieved significant improvements over baseline configurations:

.. list-table:: Performance Improvements
   :header-rows: 1
   :widths: 30 20 20 30

   * - Metric
     - Baseline
     - With CBS
     - Improvement
   * - Frame Loss Rate
     - 21.5%
     - 0.67%
     - **96.9% ⬇**
   * - Average Jitter
     - 42.3ms
     - 3.1ms
     - **92.7% ⬇**
   * - Average Latency
     - 68.4ms
     - 8.3ms
     - **87.9% ⬇**
   * - Bandwidth Guarantee
     - 55%
     - 98%
     - **78% ⬆**

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   api_reference
   tutorials
   benchmarking
   development
   research_results

API Reference
-------------

.. toctree::
   :maxdepth: 2

   api/cbs_calculator
   api/data_analyzer  
   api/traffic_generator
   api/performance_benchmark

Tutorials
---------

.. toctree::
   :maxdepth: 1

   tutorials/basic_usage
   tutorials/advanced_configuration
   tutorials/custom_traffic_profiles
   tutorials/performance_analysis
   tutorials/integration_guide

Development
-----------

.. toctree::
   :maxdepth: 1

   development/contributing
   development/testing
   development/architecture
   development/release_process

Research & Publications
-----------------------

.. toctree::
   :maxdepth: 1

   research/paper_korean
   research/paper_english
   research/experimental_setup
   research/results_analysis

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`