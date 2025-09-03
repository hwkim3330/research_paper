#!/usr/bin/env python3
"""
Real-Time CBS Monitoring Dashboard
Interactive web dashboard for monitoring CBS performance and network metrics
"""

import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import argparse
import psutil
import socket
import subprocess

# Web framework
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Data processing
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

# Local imports
import sys
sys.path.append(str(Path(__file__).parent))

from cbs_calculator import CBSCalculator, StreamConfig, TrafficType, CBSParameters
from data_analyzer import CBSDataAnalyzer
from performance_benchmark import CBSPerformanceBenchmark

class CBSMonitoringDashboard:
    """Real-time CBS monitoring dashboard"""
    
    def __init__(self, port: int = 5000, debug: bool = False):
        """Initialize dashboard"""
        self.app = Flask(__name__, template_folder='../dashboard/templates', static_folder='../dashboard/static')
        self.app.config['SECRET_KEY'] = 'cbs-dashboard-secret-key'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        CORS(self.app)
        
        self.port = port
        self.debug = debug
        
        # Initialize components
        self.calculator = CBSCalculator()
        self.analyzer = None
        self.benchmark = CBSPerformanceBenchmark()
        
        # Monitoring data
        self.monitoring_data = {
            'system_metrics': [],
            'network_metrics': [],
            'cbs_metrics': [],
            'alerts': [],
            'stream_status': {}
        }
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.update_interval = 5  # seconds
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Setup routes
        self._setup_routes()
        
        # Setup WebSocket events
        self._setup_socketio_events()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO if not self.debug else logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/status')
        def api_status():
            """Get dashboard status"""
            return jsonify({
                'status': 'running',
                'monitoring_active': self.monitoring_active,
                'uptime_seconds': time.time() - self.start_time if hasattr(self, 'start_time') else 0,
                'streams_monitored': len(self.monitoring_data['stream_status'])
            })
        
        @self.app.route('/api/system-metrics')
        def api_system_metrics():
            """Get latest system metrics"""
            return jsonify({
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_used_gb': psutil.virtual_memory().used / (1024**3),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'network_connections': len(psutil.net_connections()),
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/network-metrics')
        def api_network_metrics():
            """Get network interface statistics"""
            try:
                net_stats = psutil.net_io_counters(pernic=True)
                interfaces = []
                
                for interface, stats in net_stats.items():
                    if interface.startswith(('eth', 'en', 'wlan', 'lo')):
                        interfaces.append({
                            'interface': interface,
                            'bytes_sent': stats.bytes_sent,
                            'bytes_recv': stats.bytes_recv,
                            'packets_sent': stats.packets_sent,
                            'packets_recv': stats.packets_recv,
                            'errors_in': stats.errin,
                            'errors_out': stats.errout,
                            'drops_in': stats.dropin,
                            'drops_out': stats.dropout
                        })
                
                return jsonify({
                    'interfaces': interfaces,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/cbs-metrics')
        def api_cbs_metrics():
            """Get CBS-specific metrics"""
            return jsonify({
                'recent_metrics': self.monitoring_data['cbs_metrics'][-50:],  # Last 50 entries
                'stream_status': self.monitoring_data['stream_status'],
                'alerts': self.monitoring_data['alerts'][-10:],  # Last 10 alerts
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/stream-config', methods=['GET', 'POST'])
        def api_stream_config():
            """Get/Set stream configuration"""
            if request.method == 'POST':
                try:
                    config_data = request.get_json()
                    # Process stream configuration
                    self._update_stream_config(config_data)
                    return jsonify({'status': 'success'})
                except Exception as e:
                    return jsonify({'error': str(e)}), 400
            else:
                # Return current stream configuration
                return jsonify({
                    'streams': [stream.__dict__ for stream in getattr(self, 'current_streams', [])],
                    'calculator_settings': {
                        'link_speed_mbps': self.calculator.link_speed_mbps
                    }
                })
        
        @self.app.route('/api/calculate-cbs', methods=['POST'])
        def api_calculate_cbs():
            """Calculate CBS parameters via API"""
            try:
                stream_data = request.get_json()
                
                # Create stream config
                stream = StreamConfig(
                    name=stream_data['name'],
                    traffic_type=TrafficType(stream_data['traffic_type']),
                    bitrate_mbps=float(stream_data['bitrate_mbps']),
                    fps=int(stream_data['fps']),
                    resolution=stream_data['resolution'],
                    priority=int(stream_data['priority']),
                    max_latency_ms=float(stream_data['max_latency_ms']),
                    max_jitter_ms=float(stream_data['max_jitter_ms'])
                )
                
                # Calculate parameters
                params = self.calculator.calculate_cbs_params(stream)
                
                # Calculate additional metrics
                delay_analysis = self.calculator.calculate_theoretical_delay(stream, params)
                burst_analysis = self.calculator.calculate_burst_capacity(params)
                
                return jsonify({
                    'stream': stream.__dict__,
                    'cbs_parameters': params.__dict__,
                    'delay_analysis': delay_analysis,
                    'burst_analysis': burst_analysis,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"CBS calculation error: {e}")
                return jsonify({'error': str(e)}), 400
        
        @self.app.route('/api/start-monitoring', methods=['POST'])
        def api_start_monitoring():
            """Start real-time monitoring"""
            if not self.monitoring_active:
                self.start_monitoring()
                return jsonify({'status': 'monitoring started'})
            else:
                return jsonify({'status': 'monitoring already active'})
        
        @self.app.route('/api/stop-monitoring', methods=['POST'])
        def api_stop_monitoring():
            """Stop real-time monitoring"""
            if self.monitoring_active:
                self.stop_monitoring()
                return jsonify({'status': 'monitoring stopped'})
            else:
                return jsonify({'status': 'monitoring not active'})
        
        @self.app.route('/api/benchmark', methods=['POST'])
        def api_run_benchmark():
            """Run performance benchmark"""
            try:
                config = request.get_json() or {}
                test_type = config.get('test_type', 'calculation')
                iterations = config.get('iterations', 3)
                
                # Run benchmark in background thread
                def run_benchmark():
                    try:
                        if test_type == 'calculation':
                            result = self.benchmark.benchmark_cbs_calculation_performance()
                        elif test_type == 'optimization':
                            result = self.benchmark.benchmark_parameter_optimization()
                        elif test_type == 'scalability':
                            result = self.benchmark.benchmark_scalability()
                        elif test_type == 'memory':
                            result = self.benchmark.benchmark_memory_usage()
                        else:
                            return
                        
                        # Emit results via WebSocket
                        self.socketio.emit('benchmark_result', {
                            'result': result.__dict__,
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception as e:
                        self.socketio.emit('benchmark_error', {
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        })
                
                threading.Thread(target=run_benchmark, daemon=True).start()
                
                return jsonify({'status': 'benchmark started'})
                
            except Exception as e:
                return jsonify({'error': str(e)}), 400
        
        @self.app.route('/api/export-data', methods=['POST'])
        def api_export_data():
            """Export monitoring data"""
            try:
                format_type = request.get_json().get('format', 'json')
                
                if format_type == 'json':
                    filename = f"cbs_monitoring_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(filename, 'w') as f:
                        json.dump(self.monitoring_data, f, indent=2, default=str)
                elif format_type == 'csv':
                    filename = f"cbs_monitoring_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df = pd.DataFrame(self.monitoring_data['cbs_metrics'])
                    df.to_csv(filename, index=False)
                
                return jsonify({'status': 'data exported', 'filename': filename})
                
            except Exception as e:
                return jsonify({'error': str(e)}), 400
    
    def _setup_socketio_events(self):
        """Setup WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            self.logger.info(f"Client connected: {request.sid}")
            emit('status', {'message': 'Connected to CBS Dashboard'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            self.logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('request_update')
        def handle_request_update():
            """Handle request for data update"""
            self._emit_monitoring_data()
    
    def _update_stream_config(self, config_data: Dict[str, Any]):
        """Update stream configuration"""
        try:
            streams = []
            for stream_data in config_data.get('streams', []):
                stream = StreamConfig(
                    name=stream_data['name'],
                    traffic_type=TrafficType(stream_data['traffic_type']),
                    bitrate_mbps=float(stream_data['bitrate_mbps']),
                    fps=int(stream_data['fps']),
                    resolution=stream_data['resolution'],
                    priority=int(stream_data['priority']),
                    max_latency_ms=float(stream_data['max_latency_ms']),
                    max_jitter_ms=float(stream_data['max_jitter_ms'])
                )
                streams.append(stream)
            
            self.current_streams = streams
            
            # Recalculate CBS parameters
            if streams:
                params = self.calculator.optimize_parameters(streams)
                self.monitoring_data['stream_status'] = {}
                
                for stream in streams:
                    param = params[stream.name]
                    delay_analysis = self.calculator.calculate_theoretical_delay(stream, param)
                    
                    self.monitoring_data['stream_status'][stream.name] = {
                        'stream': stream.__dict__,
                        'parameters': param.__dict__,
                        'delay_analysis': delay_analysis,
                        'status': 'configured',
                        'last_update': datetime.now().isoformat()
                    }
            
            self.logger.info(f"Stream configuration updated: {len(streams)} streams")
            
        except Exception as e:
            self.logger.error(f"Stream configuration error: {e}")
            raise
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("Real-time monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        self.logger.info("Real-time monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Collect network metrics
                self._collect_network_metrics()
                
                # Collect CBS-specific metrics
                self._collect_cbs_metrics()
                
                # Check for alerts
                self._check_alerts()
                
                # Emit data via WebSocket
                self._emit_monitoring_data()
                
                # Clean up old data (keep last 1000 entries)
                self._cleanup_old_data()
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
            
            time.sleep(self.update_interval)
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            metric = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_used_gb': psutil.virtual_memory().used / (1024**3),
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
                'process_count': len(psutil.pids())
            }
            
            self.monitoring_data['system_metrics'].append(metric)
            
        except Exception as e:
            self.logger.error(f"System metrics collection error: {e}")
    
    def _collect_network_metrics(self):
        """Collect network interface metrics"""
        try:
            net_stats = psutil.net_io_counters()
            
            metric = {
                'timestamp': datetime.now().isoformat(),
                'bytes_sent_total': net_stats.bytes_sent,
                'bytes_recv_total': net_stats.bytes_recv,
                'packets_sent_total': net_stats.packets_sent,
                'packets_recv_total': net_stats.packets_recv,
                'errors_in_total': net_stats.errin,
                'errors_out_total': net_stats.errout,
                'drops_in_total': net_stats.dropin,
                'drops_out_total': net_stats.dropout
            }
            
            # Calculate rates if we have previous data
            if len(self.monitoring_data['network_metrics']) > 0:
                prev = self.monitoring_data['network_metrics'][-1]
                time_diff = (datetime.fromisoformat(metric['timestamp']) - 
                           datetime.fromisoformat(prev['timestamp'])).total_seconds()
                
                if time_diff > 0:
                    metric['bytes_sent_rate'] = (metric['bytes_sent_total'] - prev['bytes_sent_total']) / time_diff
                    metric['bytes_recv_rate'] = (metric['bytes_recv_total'] - prev['bytes_recv_total']) / time_diff
                    metric['packets_sent_rate'] = (metric['packets_sent_total'] - prev['packets_sent_total']) / time_diff
                    metric['packets_recv_rate'] = (metric['packets_recv_total'] - prev['packets_recv_total']) / time_diff
            
            self.monitoring_data['network_metrics'].append(metric)
            
        except Exception as e:
            self.logger.error(f"Network metrics collection error: {e}")
    
    def _collect_cbs_metrics(self):
        """Collect CBS-specific metrics"""
        try:
            # Simulate CBS metrics (in real implementation, would query actual hardware)
            metric = {
                'timestamp': datetime.now().isoformat(),
                'active_streams': len(self.monitoring_data['stream_status']),
                'total_reserved_bandwidth': sum(
                    stream_info.get('parameters', {}).get('reserved_bandwidth_mbps', 0)
                    for stream_info in self.monitoring_data['stream_status'].values()
                ),
                'network_utilization_percent': 0,  # Would be calculated from real data
                'avg_efficiency_percent': 0,       # Would be calculated from real data
                'credit_overflows': 0,             # Hardware counter
                'credit_underflows': 0,            # Hardware counter
                'queue_drops': 0,                  # Hardware counter
            }
            
            # Calculate derived metrics
            if metric['active_streams'] > 0:
                total_actual = sum(
                    stream_info.get('stream', {}).get('bitrate_mbps', 0)
                    for stream_info in self.monitoring_data['stream_status'].values()
                )
                
                metric['network_utilization_percent'] = (total_actual / self.calculator.link_speed_mbps) * 100
                
                if metric['total_reserved_bandwidth'] > 0:
                    metric['avg_efficiency_percent'] = (total_actual / metric['total_reserved_bandwidth']) * 100
            
            self.monitoring_data['cbs_metrics'].append(metric)
            
        except Exception as e:
            self.logger.error(f"CBS metrics collection error: {e}")
    
    def _check_alerts(self):
        """Check for alert conditions"""
        try:
            # Check system resource usage
            if len(self.monitoring_data['system_metrics']) > 0:
                latest = self.monitoring_data['system_metrics'][-1]
                
                if latest['cpu_percent'] > 80:
                    self._add_alert('warning', 'High CPU usage', f"CPU usage: {latest['cpu_percent']:.1f}%")
                
                if latest['memory_percent'] > 80:
                    self._add_alert('warning', 'High memory usage', f"Memory usage: {latest['memory_percent']:.1f}%")
            
            # Check network utilization
            if len(self.monitoring_data['cbs_metrics']) > 0:
                latest = self.monitoring_data['cbs_metrics'][-1]
                
                if latest['network_utilization_percent'] > 80:
                    self._add_alert('warning', 'High network utilization', 
                                  f"Network utilization: {latest['network_utilization_percent']:.1f}%")
                
                if latest['avg_efficiency_percent'] < 70:
                    self._add_alert('info', 'Low bandwidth efficiency', 
                                  f"Efficiency: {latest['avg_efficiency_percent']:.1f}%")
            
            # Check stream status
            for stream_name, stream_info in self.monitoring_data['stream_status'].items():
                delay_analysis = stream_info.get('delay_analysis', {})
                stream_config = stream_info.get('stream', {})
                
                total_delay = delay_analysis.get('total_delay_ms', 0)
                max_latency = stream_config.get('max_latency_ms', float('inf'))
                
                if total_delay > max_latency:
                    self._add_alert('error', f'Latency violation: {stream_name}', 
                                  f"Actual: {total_delay:.3f}ms, Limit: {max_latency:.3f}ms")
            
        except Exception as e:
            self.logger.error(f"Alert checking error: {e}")
    
    def _add_alert(self, level: str, title: str, message: str):
        """Add an alert to the monitoring data"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'title': title,
            'message': message
        }
        
        self.monitoring_data['alerts'].append(alert)
        self.logger.info(f"Alert added: {level} - {title}: {message}")
    
    def _emit_monitoring_data(self):
        """Emit monitoring data via WebSocket"""
        try:
            # Prepare data for transmission (last 50 entries)
            data = {
                'system_metrics': self.monitoring_data['system_metrics'][-50:],
                'network_metrics': self.monitoring_data['network_metrics'][-50:],
                'cbs_metrics': self.monitoring_data['cbs_metrics'][-50:],
                'stream_status': self.monitoring_data['stream_status'],
                'alerts': self.monitoring_data['alerts'][-10:],
                'timestamp': datetime.now().isoformat()
            }
            
            self.socketio.emit('monitoring_update', data)
            
        except Exception as e:
            self.logger.error(f"Data emission error: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data to prevent memory issues"""
        max_entries = 1000
        
        for key in ['system_metrics', 'network_metrics', 'cbs_metrics']:
            if len(self.monitoring_data[key]) > max_entries:
                self.monitoring_data[key] = self.monitoring_data[key][-max_entries:]
        
        # Keep alerts for last 24 hours
        if len(self.monitoring_data['alerts']) > 100:
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.monitoring_data['alerts'] = [
                alert for alert in self.monitoring_data['alerts']
                if datetime.fromisoformat(alert['timestamp']) > cutoff_time
            ]
    
    def run(self):
        """Run the dashboard"""
        self.start_time = time.time()
        self.logger.info(f"Starting CBS Monitoring Dashboard on port {self.port}")
        
        # Create templates directory if it doesn't exist
        template_dir = Path(__file__).parent.parent / 'dashboard' / 'templates'
        template_dir.mkdir(parents=True, exist_ok=True)
        
        # Create basic dashboard template if it doesn't exist
        dashboard_template = template_dir / 'dashboard.html'
        if not dashboard_template.exists():
            self._create_dashboard_template(dashboard_template)
        
        try:
            self.socketio.run(
                self.app,
                host='0.0.0.0',
                port=self.port,
                debug=self.debug,
                allow_unsafe_werkzeug=True
            )
        except KeyboardInterrupt:
            self.logger.info("Dashboard shutdown requested")
        finally:
            self.stop_monitoring()
    
    def _create_dashboard_template(self, template_path: Path):
        """Create basic dashboard HTML template"""
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CBS Monitoring Dashboard</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .metric-card { margin: 10px 0; }
        .alert-panel { max-height: 300px; overflow-y: auto; }
        .chart-container { height: 400px; margin: 20px 0; }
        .status-indicator { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        .status-ok { background-color: #28a745; }
        .status-warning { background-color: #ffc107; }
        .status-error { background-color: #dc3545; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <nav class="navbar navbar-dark bg-primary">
                    <span class="navbar-brand">🚗 CBS Monitoring Dashboard</span>
                    <div>
                        <button id="start-monitoring" class="btn btn-success btn-sm">Start Monitoring</button>
                        <button id="stop-monitoring" class="btn btn-danger btn-sm">Stop Monitoring</button>
                        <span id="status-indicator" class="status-indicator status-error"></span>
                        <span id="status-text">Disconnected</span>
                    </div>
                </nav>
            </div>
        </div>
        
        <div class="row mt-3">
            <!-- System Metrics -->
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-header">System Metrics</div>
                    <div class="card-body">
                        <p>CPU: <span id="cpu-usage">0%</span></p>
                        <p>Memory: <span id="memory-usage">0%</span></p>
                        <p>Disk: <span id="disk-usage">0%</span></p>
                        <p>Network Connections: <span id="network-connections">0</span></p>
                    </div>
                </div>
            </div>
            
            <!-- CBS Metrics -->
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-header">CBS Metrics</div>
                    <div class="card-body">
                        <p>Active Streams: <span id="active-streams">0</span></p>
                        <p>Network Utilization: <span id="network-utilization">0%</span></p>
                        <p>Bandwidth Efficiency: <span id="bandwidth-efficiency">0%</span></p>
                        <p>Reserved BW: <span id="reserved-bandwidth">0 Mbps</span></p>
                    </div>
                </div>
            </div>
            
            <!-- Stream Status -->
            <div class="col-md-6">
                <div class="card metric-card">
                    <div class="card-header">Stream Status</div>
                    <div class="card-body">
                        <div id="stream-status-list">
                            <p class="text-muted">No streams configured</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Charts -->
            <div class="col-md-6">
                <div class="chart-container">
                    <div id="cpu-memory-chart"></div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="chart-container">
                    <div id="network-utilization-chart"></div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Alerts -->
            <div class="col-12">
                <div class="card">
                    <div class="card-header">Recent Alerts</div>
                    <div class="card-body alert-panel">
                        <div id="alerts-list">
                            <p class="text-muted">No alerts</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Initialize WebSocket connection
        const socket = io();
        
        // Connection status
        socket.on('connect', function() {
            document.getElementById('status-indicator').className = 'status-indicator status-ok';
            document.getElementById('status-text').textContent = 'Connected';
        });
        
        socket.on('disconnect', function() {
            document.getElementById('status-indicator').className = 'status-indicator status-error';
            document.getElementById('status-text').textContent = 'Disconnected';
        });
        
        // Handle monitoring data updates
        socket.on('monitoring_update', function(data) {
            updateSystemMetrics(data.system_metrics);
            updateCBSMetrics(data.cbs_metrics);
            updateStreamStatus(data.stream_status);
            updateAlerts(data.alerts);
            updateCharts(data);
        });
        
        // Button event handlers
        document.getElementById('start-monitoring').addEventListener('click', function() {
            fetch('/api/start-monitoring', {method: 'POST'});
        });
        
        document.getElementById('stop-monitoring').addEventListener('click', function() {
            fetch('/api/stop-monitoring', {method: 'POST'});
        });
        
        // Update functions
        function updateSystemMetrics(metrics) {
            if (metrics && metrics.length > 0) {
                const latest = metrics[metrics.length - 1];
                document.getElementById('cpu-usage').textContent = latest.cpu_percent + '%';
                document.getElementById('memory-usage').textContent = latest.memory_percent + '%';
                document.getElementById('disk-usage').textContent = latest.disk_usage_percent + '%';
            }
        }
        
        function updateCBSMetrics(metrics) {
            if (metrics && metrics.length > 0) {
                const latest = metrics[metrics.length - 1];
                document.getElementById('active-streams').textContent = latest.active_streams;
                document.getElementById('network-utilization').textContent = latest.network_utilization_percent.toFixed(1) + '%';
                document.getElementById('bandwidth-efficiency').textContent = latest.avg_efficiency_percent.toFixed(1) + '%';
                document.getElementById('reserved-bandwidth').textContent = latest.total_reserved_bandwidth.toFixed(1) + ' Mbps';
            }
        }
        
        function updateStreamStatus(streams) {
            const container = document.getElementById('stream-status-list');
            if (Object.keys(streams).length === 0) {
                container.innerHTML = '<p class="text-muted">No streams configured</p>';
                return;
            }
            
            let html = '';
            for (const [name, info] of Object.entries(streams)) {
                const stream = info.stream;
                const params = info.parameters;
                const delay = info.delay_analysis;
                
                const statusClass = delay.total_delay_ms <= stream.max_latency_ms ? 'status-ok' : 'status-error';
                
                html += `
                    <div class="mb-2">
                        <span class="status-indicator ${statusClass}"></span>
                        <strong>${name}</strong> (TC${stream.priority}) - ${stream.bitrate_mbps} Mbps
                        <br><small class="text-muted">Delay: ${delay.total_delay_ms.toFixed(3)}ms / ${stream.max_latency_ms}ms</small>
                    </div>
                `;
            }
            container.innerHTML = html;
        }
        
        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-list');
            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<p class="text-muted">No alerts</p>';
                return;
            }
            
            let html = '';
            alerts.reverse().forEach(alert => {
                const alertClass = alert.level === 'error' ? 'alert-danger' : 
                                 alert.level === 'warning' ? 'alert-warning' : 'alert-info';
                const timestamp = new Date(alert.timestamp).toLocaleTimeString();
                
                html += `
                    <div class="alert ${alertClass} alert-sm mb-1">
                        <strong>${alert.title}</strong> (${timestamp})<br>
                        <small>${alert.message}</small>
                    </div>
                `;
            });
            container.innerHTML = html;
        }
        
        function updateCharts(data) {
            // Update CPU/Memory chart
            if (data.system_metrics && data.system_metrics.length > 0) {
                const timestamps = data.system_metrics.map(m => new Date(m.timestamp));
                const cpuData = data.system_metrics.map(m => m.cpu_percent);
                const memoryData = data.system_metrics.map(m => m.memory_percent);
                
                const cpuMemoryTrace1 = {
                    x: timestamps,
                    y: cpuData,
                    type: 'scatter',
                    name: 'CPU %',
                    line: {color: 'red'}
                };
                
                const cpuMemoryTrace2 = {
                    x: timestamps,
                    y: memoryData,
                    type: 'scatter',
                    name: 'Memory %',
                    line: {color: 'blue'}
                };
                
                Plotly.newPlot('cpu-memory-chart', [cpuMemoryTrace1, cpuMemoryTrace2], {
                    title: 'System Resource Usage',
                    xaxis: {title: 'Time'},
                    yaxis: {title: 'Percentage (%)', range: [0, 100]}
                });
            }
            
            // Update network utilization chart
            if (data.cbs_metrics && data.cbs_metrics.length > 0) {
                const timestamps = data.cbs_metrics.map(m => new Date(m.timestamp));
                const utilization = data.cbs_metrics.map(m => m.network_utilization_percent);
                
                const networkTrace = {
                    x: timestamps,
                    y: utilization,
                    type: 'scatter',
                    name: 'Network Utilization %',
                    line: {color: 'green'},
                    fill: 'tozeroy'
                };
                
                Plotly.newPlot('network-utilization-chart', [networkTrace], {
                    title: 'Network Utilization',
                    xaxis: {title: 'Time'},
                    yaxis: {title: 'Utilization (%)', range: [0, 100]}
                });
            }
        }
        
        // Request initial update
        socket.emit('request_update');
        
        // Auto-refresh every 10 seconds
        setInterval(function() {
            socket.emit('request_update');
        }, 10000);
    </script>
</body>
</html>'''
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='CBS Real-Time Monitoring Dashboard')
    parser.add_argument('--port', type=int, default=5000, help='Server port (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--auto-monitor', action='store_true', help='Start monitoring automatically')
    
    args = parser.parse_args()
    
    # Create and run dashboard
    dashboard = CBSMonitoringDashboard(port=args.port, debug=args.debug)
    
    if args.auto_monitor:
        dashboard.start_monitoring()
    
    print(f"🚀 Starting CBS Monitoring Dashboard")
    print(f"🌐 Dashboard URL: http://localhost:{args.port}")
    print(f"📊 WebSocket enabled for real-time updates")
    print(f"🔧 Debug mode: {'enabled' if args.debug else 'disabled'}")
    print()
    print("Press Ctrl+C to stop the dashboard")
    
    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")

if __name__ == "__main__":
    main()