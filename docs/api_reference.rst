API Reference
=============

This section provides detailed API documentation for all modules in the CBS Research Project.

Core Modules
------------

CBS Calculator
~~~~~~~~~~~~~~

.. automodule:: cbs_calculator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: cbs_calculator.CBSCalculator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: cbs_calculator.CBSParameters
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: cbs_calculator.StreamConfig
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: cbs_calculator.TrafficType
   :members:
   :undoc-members:
   :show-inheritance:

Data Analyzer
~~~~~~~~~~~~~

.. automodule:: data_analyzer
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: data_analyzer.CBSDataAnalyzer
   :members:
   :undoc-members:
   :show-inheritance:

Traffic Generator
~~~~~~~~~~~~~~~~~

.. automodule:: traffic_generator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: traffic_generator.TrafficGenerator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: traffic_generator.TrafficProfile
   :members:
   :undoc-members:
   :show-inheritance:

Performance Benchmark
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: performance_benchmark
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: performance_benchmark.CBSPerformanceBenchmark
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: performance_benchmark.BenchmarkResult
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: performance_benchmark.BenchmarkConfig
   :members:
   :undoc-members:
   :show-inheritance:

Data Structures
---------------

The CBS Research Project uses several key data structures to represent network configurations and results.

Traffic Types
~~~~~~~~~~~~~

.. autoclass:: cbs_calculator.TrafficType
   :members:

   Enumeration of supported traffic types in automotive networks:

   - **SAFETY_CRITICAL**: Emergency control signals (highest priority)
   - **VIDEO_4K**: 4K video streams from cameras
   - **VIDEO_1080P**: HD video streams  
   - **VIDEO_720P**: Standard definition video
   - **LIDAR**: LiDAR sensor data
   - **RADAR**: Radar sensor data
   - **V2X**: Vehicle-to-everything communication
   - **CONTROL**: General control messages
   - **INFOTAINMENT**: Entertainment and information services
   - **DIAGNOSTICS**: System diagnostics and telemetry
   - **OTA**: Over-the-air updates

Stream Configuration
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: cbs_calculator.StreamConfig

   Represents a network traffic stream with its requirements and characteristics.

   **Key Attributes:**

   - ``name`` (str): Human-readable stream identifier
   - ``traffic_type`` (TrafficType): Type of traffic for this stream
   - ``bitrate_mbps`` (float): Required bitrate in Megabits per second
   - ``fps`` (int): Frame rate for video streams
   - ``resolution`` (str): Video resolution (e.g., "1920x1080")
   - ``priority`` (int): Traffic priority (0-7, higher numbers = higher priority)
   - ``max_latency_ms`` (float): Maximum acceptable latency in milliseconds
   - ``max_jitter_ms`` (float): Maximum acceptable jitter in milliseconds

   **Example:**

   .. code-block:: python

      stream = StreamConfig(
          name="Front_Camera_4K",
          traffic_type=TrafficType.VIDEO_4K,
          bitrate_mbps=25.0,
          fps=60,
          resolution="3840x2160",
          priority=6,
          max_latency_ms=20.0,
          max_jitter_ms=3.0
      )

CBS Parameters
~~~~~~~~~~~~~~

.. autoclass:: cbs_calculator.CBSParameters

   Contains the calculated CBS parameters for a traffic stream.

   **Key Attributes:**

   - ``idle_slope`` (int): Rate at which credits increase when queue is empty (bps)
   - ``send_slope`` (int): Rate at which credits decrease during transmission (bps, negative)
   - ``hi_credit`` (int): Maximum credit value (bits)
   - ``lo_credit`` (int): Minimum credit value (bits, negative)
   - ``reserved_bandwidth_mbps`` (float): Total reserved bandwidth including overhead
   - ``actual_bandwidth_mbps`` (float): Actual stream bandwidth requirement
   - ``efficiency_percent`` (float): Efficiency ratio (actual/reserved * 100)

   **Mathematical Relationships:**

   .. math::

      \text{sendSlope} = \text{idleSlope} - \text{linkSpeed}

   .. math::

      \text{loCredit} = -\text{hiCredit}

   .. math::

      \text{efficiency} = \frac{\text{actualBW}}{\text{reservedBW}} \times 100\%

Utility Functions
-----------------

The API also provides several utility functions for common operations.

Configuration Export
~~~~~~~~~~~~~~~~~~~~

.. automethod:: cbs_calculator.CBSCalculator.generate_config_file

   Exports CBS parameters to industry-standard YAML format.

   **Generated YAML Structure:**

   .. code-block:: yaml

      cbs-configuration:
        link-speed-mbps: 1000
        timestamp: "2025-09-02T10:00:00Z"
        streams:
          - name: "Front_Camera_4K"
            type: "video_4k"
            priority: 6
            bitrate-mbps: 25.0
            cbs-parameters:
              idle-slope: 30000000
              send-slope: -970000000
              hi-credit: 365
              lo-credit: -365

Performance Analysis
~~~~~~~~~~~~~~~~~~~~

.. automethod:: cbs_calculator.CBSCalculator.calculate_theoretical_delay

   Calculates theoretical delay components for a stream.

   **Returns dictionary with:**
   
   - ``propagation_delay_ms``: Physical propagation delay
   - ``processing_delay_ms``: Switch processing delay  
   - ``queuing_delay_ms``: Queuing delay from CBS shaping
   - ``total_delay_ms``: Sum of all delay components

.. automethod:: cbs_calculator.CBSCalculator.calculate_burst_capacity

   Analyzes burst handling capability of CBS configuration.

   **Returns dictionary with:**

   - ``burst_capacity_bytes``: Maximum burst size that can be handled
   - ``max_burst_duration_ms``: Maximum duration of sustainable burst
   - ``burst_capacity_packets``: Burst capacity in number of packets

Validation and Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: cbs_calculator.CBSCalculator.validate_configuration

   Validates CBS parameters and returns warnings for potential issues.

   **Common Warnings:**

   - High bandwidth utilization (>80%)
   - Very high or low credit values
   - Poor bandwidth efficiency
   - Potential parameter conflicts

.. automethod:: cbs_calculator.CBSCalculator.optimize_parameters

   Optimizes CBS parameters for multiple streams to achieve target utilization.

   **Optimization Process:**

   1. Calculate initial parameters for all streams
   2. Check total bandwidth utilization
   3. If utilization exceeds target, reduce headroom proportionally
   4. Ensure minimum QoS requirements are still met
   5. Return optimized parameter set

Error Handling
--------------

The API uses standard Python exceptions with descriptive error messages.

Common Exceptions
~~~~~~~~~~~~~~~~~

.. py:exception:: ValueError

   Raised for invalid input parameters:

   - Negative bitrates or link speeds
   - Invalid priority values (must be 0-7)
   - Conflicting stream requirements

.. py:exception:: FileNotFoundError

   Raised when configuration or data files cannot be found.

.. py:exception:: json.JSONDecodeError

   Raised when JSON configuration files are malformed.

**Example Error Handling:**

.. code-block:: python

   from src.cbs_calculator import CBSCalculator, StreamConfig, TrafficType

   try:
       calculator = CBSCalculator(link_speed_mbps=1000)
       
       # This will raise ValueError for invalid priority
       invalid_stream = StreamConfig(
           name="Invalid Stream",
           traffic_type=TrafficType.VIDEO_4K,
           bitrate_mbps=25.0,
           fps=60,
           resolution="3840x2160", 
           priority=10,  # Invalid! Must be 0-7
           max_latency_ms=20.0,
           max_jitter_ms=3.0
       )
       
       params = calculator.calculate_cbs_params(invalid_stream)
       
   except ValueError as e:
       print(f"Configuration error: {e}")
   except Exception as e:
       print(f"Unexpected error: {e}")

Constants and Enumerations
--------------------------

The following constants are defined for use throughout the API:

**Link Speeds (Mbps):**

.. code-block:: python

   LINK_SPEEDS = {
       'FAST_ETHERNET': 100,
       'GIGABIT_ETHERNET': 1000, 
       'TEN_GIGABIT_ETHERNET': 10000
   }

**Traffic Class Priorities:**

.. code-block:: python

   PRIORITY_CLASSES = {
       'BEST_EFFORT': 0,
       'BACKGROUND': 1,
       'EXCELLENT_EFFORT': 2,
       'CRITICAL_APPLICATIONS': 3,
       'VIDEO': 4,
       'VOICE': 5, 
       'INTERNETWORK_CONTROL': 6,
       'NETWORK_CONTROL': 7
   }

**Frame Sizes (Bytes):**

.. code-block:: python

   FRAME_SIZES = {
       'MIN_ETHERNET': 64,
       'MAX_ETHERNET': 1518,
       'JUMBO_FRAME': 9000
   }

Type Hints
----------

The CBS Research Project uses comprehensive type hints for better code clarity and IDE support:

.. code-block:: python

   from typing import Dict, List, Tuple, Optional, Any
   from dataclasses import dataclass

   def calculate_multi_stream(
       self, 
       streams: List[StreamConfig]
   ) -> Dict[str, CBSParameters]:
       """Calculate CBS parameters for multiple streams."""
       pass

   def analyze_interference_impact(
       self, 
       streams: List[StreamConfig],
       interfering_traffic_mbps: float = 0
   ) -> Dict[str, Any]:
       """Analyze impact of interfering traffic."""
       pass

Extension Points
----------------

The API is designed for extensibility:

**Custom Traffic Types:**

.. code-block:: python

   # Extend TrafficType enum for custom applications
   class CustomTrafficType(TrafficType):
       CUSTOM_SENSOR = "custom_sensor"
       PROPRIETARY_CONTROL = "proprietary_control"

**Custom Analysis Functions:**

.. code-block:: python

   class ExtendedCBSCalculator(CBSCalculator):
       def custom_analysis(self, streams: List[StreamConfig]) -> Dict[str, Any]:
           """Add custom analysis functionality."""
           # Your custom implementation
           pass

**Plugin Architecture:**

The system supports plugins for custom traffic generators, analyzers, and benchmark tests. See the [Development Guide](development/architecture.html) for details on creating plugins.