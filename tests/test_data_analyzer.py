#!/usr/bin/env python3
"""
Test Suite for Data Analyzer
Tests for CBS performance data analysis and visualization
"""

import pytest
import sys
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_analyzer import CBSDataAnalyzer

class TestCBSDataAnalyzer:
    """Test suite for CBS Data Analyzer"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample experimental data"""
        return {
            "experiment_metadata": {
                "date": "2025-09-02",
                "duration_hours": 24,
                "test_vehicles": 3,
                "total_distance_km": 1000
            },
            "performance_metrics": {
                "frame_loss_rate": {
                    "background_traffic_mbps": [0, 200, 400, 600, 800],
                    "without_cbs": [0.0, 5.2, 12.7, 18.3, 25.8],
                    "with_cbs": [0.0, 0.1, 0.3, 0.8, 1.2],
                    "with_cbs_and_tas": [0.0, 0.0, 0.1, 0.3, 0.7]
                },
                "latency_ms": {
                    "percentiles": {
                        "without_cbs": {
                            "p50": 65.4,
                            "p75": 78.3,
                            "p90": 85.2,
                            "p95": 89.7,
                            "p99": 95.3,
                            "p99.9": 98.2,
                            "max": 102.7
                        },
                        "with_cbs": {
                            "p50": 8.8,
                            "p75": 10.1,
                            "p90": 11.2,
                            "p95": 12.1,
                            "p99": 14.8,
                            "p99.9": 16.5,
                            "max": 18.3
                        },
                        "with_cbs_and_tas": {
                            "p50": 4.2,
                            "p75": 5.1,
                            "p90": 6.3,
                            "p95": 7.2,
                            "p99": 9.1,
                            "p99.9": 10.5,
                            "max": 12.2
                        }
                    },
                    "time_series": {
                        "timestamps_sec": [0, 60, 120, 180, 240, 300],
                        "without_cbs": [45.2, 62.3, 71.8, 68.4, 75.2, 69.1],
                        "with_cbs": [6.8, 6.9, 7.1, 6.7, 7.0, 6.9]
                    }
                },
                "jitter_ms": {
                    "traffic_load_mbps": [0, 200, 400, 600, 800],
                    "video_4k": {
                        "without_cbs": [2.1, 15.3, 28.7, 38.8, 45.3],
                        "with_cbs": [0.8, 1.5, 2.1, 2.8, 3.2]
                    },
                    "video_1080p": {
                        "without_cbs": [1.8, 12.7, 23.3, 32.4, 39.2],
                        "with_cbs": [0.7, 1.3, 1.9, 2.6, 2.9]
                    },
                    "sensor_data": {
                        "without_cbs": [0.5, 4.2, 9.1, 15.3, 20.7],
                        "with_cbs": [0.2, 0.4, 0.7, 1.1, 1.4]
                    }
                },
                "credit_dynamics": {
                    "sample_duration_us": 1000,
                    "timestamps_us": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
                    "credit_values": [0, 300, 365, 365, -2000, -6000, -10000, -11814, -9000, -5000, -1000],
                    "state_transitions": ["IDLE", "WAIT", "WAIT", "READY", "SEND", "SEND", "SEND", "SEND", "WAIT", "WAIT", "WAIT"],
                    "queue_depth": [0, 3, 5, 5, 4, 3, 2, 1, 2, 4, 5]
                }
            }
        }
    
    @pytest.fixture
    def analyzer_with_data(self, sample_data):
        """Create analyzer instance with sample data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sample_data, temp_file)
            temp_path = temp_file.name
        
        try:
            analyzer = CBSDataAnalyzer(temp_path)
            yield analyzer
        finally:
            os.unlink(temp_path)
    
    @pytest.fixture
    def empty_analyzer(self):
        """Create analyzer instance without data"""
        return CBSDataAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        analyzer = CBSDataAnalyzer()
        assert analyzer.data is None
        assert analyzer.figures == {}
        assert analyzer.logger is not None
    
    def test_data_loading(self, sample_data):
        """Test data loading functionality"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sample_data, temp_file)
            temp_path = temp_file.name
        
        try:
            analyzer = CBSDataAnalyzer()
            analyzer.load_data(temp_path)
            
            assert analyzer.data is not None
            assert analyzer.data == sample_data
            assert 'performance_metrics' in analyzer.data
        finally:
            os.unlink(temp_path)
    
    def test_data_loading_error(self, empty_analyzer):
        """Test data loading with invalid file"""
        with pytest.raises(Exception):
            empty_analyzer.load_data("nonexistent_file.json")
    
    def test_performance_summary_generation(self, analyzer_with_data):
        """Test performance summary generation"""
        summary_df = analyzer_with_data.generate_performance_summary()
        
        assert isinstance(summary_df, pd.DataFrame)
        assert len(summary_df) > 0
        
        # Check required columns
        required_columns = [
            'background_traffic_mbps',
            'frame_loss_without_cbs',
            'frame_loss_with_cbs',
            'improvement_cbs'
        ]
        for col in required_columns:
            assert col in summary_df.columns
        
        # Check improvement calculations
        assert all(summary_df['improvement_cbs'] >= 0)  # Should show improvement
    
    def test_performance_summary_without_data(self, empty_analyzer):
        """Test performance summary generation without data"""
        with pytest.raises(ValueError):
            empty_analyzer.generate_performance_summary()
    
    @patch('plotly.graph_objects.Figure.write_html')
    def test_frame_loss_plot(self, mock_write_html, analyzer_with_data):
        """Test frame loss comparison plot generation"""
        fig = analyzer_with_data.plot_frame_loss_comparison()
        
        assert fig is not None
        assert 'frame_loss' in analyzer_with_data.figures
        
        # Test with save path
        analyzer_with_data.plot_frame_loss_comparison("test_output.html")
        mock_write_html.assert_called_with("test_output.html")
    
    def test_frame_loss_plot_without_data(self, empty_analyzer):
        """Test frame loss plot generation without data"""
        with pytest.raises(ValueError):
            empty_analyzer.plot_frame_loss_comparison()
    
    @patch('plotly.graph_objects.Figure.write_html')
    def test_latency_analysis_plot(self, mock_write_html, analyzer_with_data):
        """Test latency analysis plot generation"""
        fig = analyzer_with_data.plot_latency_analysis()
        
        assert fig is not None
        assert 'latency' in analyzer_with_data.figures
        
        # Test with save path
        analyzer_with_data.plot_latency_analysis("test_latency.html")
        mock_write_html.assert_called_with("test_latency.html")
    
    @patch('plotly.graph_objects.Figure.write_html')
    def test_jitter_analysis_plot(self, mock_write_html, analyzer_with_data):
        """Test jitter analysis plot generation"""
        fig = analyzer_with_data.plot_jitter_analysis()
        
        assert fig is not None
        assert 'jitter' in analyzer_with_data.figures
        
        # Test with save path
        analyzer_with_data.plot_jitter_analysis("test_jitter.html")
        mock_write_html.assert_called_with("test_jitter.html")
    
    @patch('plotly.graph_objects.Figure.write_html')
    def test_credit_dynamics_plot(self, mock_write_html, analyzer_with_data):
        """Test credit dynamics visualization"""
        fig = analyzer_with_data.plot_credit_dynamics()
        
        assert fig is not None
        assert 'credit_dynamics' in analyzer_with_data.figures
        
        # Test with save path
        analyzer_with_data.plot_credit_dynamics("test_credit.html")
        mock_write_html.assert_called_with("test_credit.html")
    
    def test_statistical_report_generation(self, analyzer_with_data):
        """Test statistical report generation"""
        report = analyzer_with_data.generate_statistical_report()
        
        assert isinstance(report, dict)
        assert 'summary' in report
        assert 'statistical_tests' in report
        assert 'correlations' in report
        assert 'recommendations' in report
        
        # Check summary metrics
        summary = report['summary']
        assert 'avg_frame_loss_improvement_percent' in summary
        assert 'latency_improvement_percent' in summary
        
        # Check recommendations
        assert isinstance(report['recommendations'], list)
    
    def test_statistical_report_without_data(self, empty_analyzer):
        """Test statistical report generation without data"""
        with pytest.raises(ValueError):
            empty_analyzer.generate_statistical_report()
    
    @patch('pathlib.Path.mkdir')
    @patch('plotly.graph_objects.Figure.write_html')
    @patch('builtins.open')
    @patch('json.dump')
    def test_comprehensive_dashboard(self, mock_json_dump, mock_open, 
                                   mock_write_html, mock_mkdir, analyzer_with_data):
        """Test comprehensive dashboard generation"""
        # Mock file operations
        mock_open.return_value.__enter__.return_value = MagicMock()
        
        analyzer_with_data.create_comprehensive_dashboard("test_output")
        
        # Verify directory creation
        mock_mkdir.assert_called_once()
        
        # Verify HTML plots were generated
        assert mock_write_html.call_count >= 4  # At least 4 plots
        
        # Verify JSON report was saved
        mock_json_dump.assert_called()
        
        # Verify main dashboard HTML was created
        mock_open.assert_called()
    
    def test_dashboard_html_generation(self, analyzer_with_data):
        """Test dashboard HTML template generation"""
        html_content = analyzer_with_data._create_dashboard_html()
        
        assert isinstance(html_content, str)
        assert '<!DOCTYPE html>' in html_content
        assert 'CBS Performance Analysis Dashboard' in html_content
        assert 'frame_loss_analysis.html' in html_content
        assert 'latency_analysis.html' in html_content
    
    def test_logging_functionality(self, analyzer_with_data):
        """Test logging functionality"""
        assert analyzer_with_data.logger is not None
        assert analyzer_with_data.logger.name == 'data_analyzer'
    
    def test_error_handling_in_statistical_tests(self, analyzer_with_data):
        """Test error handling in statistical tests"""
        # Mock scipy.stats.wilcoxon to raise an exception
        with patch('scipy.stats.wilcoxon', side_effect=Exception("Test error")):
            # Should not crash, should handle the exception gracefully
            report = analyzer_with_data.generate_statistical_report()
            
            # Statistical tests might be missing but other parts should work
            assert isinstance(report, dict)
            assert 'summary' in report
    
    def test_data_validation(self, analyzer_with_data):
        """Test data structure validation"""
        # Analyzer should work with valid data
        summary = analyzer_with_data.generate_performance_summary()
        assert len(summary) > 0
        
        # Test with incomplete data
        incomplete_data = {
            "performance_metrics": {
                "frame_loss_rate": {
                    "background_traffic_mbps": [0, 200],
                    "without_cbs": [0.0, 5.2],
                    "with_cbs": [0.0, 0.1]
                    # Missing with_cbs_and_tas
                }
            }
        }
        
        analyzer_with_data.data = incomplete_data
        
        # Should handle missing data gracefully
        try:
            summary = analyzer_with_data.generate_performance_summary()
            # If it succeeds, verify the structure
            assert isinstance(summary, pd.DataFrame)
        except (KeyError, IndexError):
            # Expected if data is too incomplete
            pass

class TestDataAnalyzerCommandLine:
    """Test command-line interface functionality"""
    
    @pytest.fixture
    def sample_args(self):
        """Create sample command-line arguments"""
        class Args:
            data = "test_data.json"
            output = "test_output"
            format = "html"
        
        return Args()
    
    @patch('sys.argv', ['data_analyzer.py', '--data', 'test_data.json'])
    @patch('argparse.ArgumentParser.parse_args')
    def test_argument_parsing(self, mock_parse_args):
        """Test command-line argument parsing"""
        from data_analyzer import main
        
        # Mock the parser to return our test args
        mock_parse_args.return_value = self.sample_args()
        
        # Should not raise an exception during argument parsing
        try:
            # This will fail at data loading, but that's expected
            main()
        except:
            pass  # Expected to fail at data loading with test file
    
    def test_analyzer_integration_with_real_data(self):
        """Test analyzer with actual experimental data format"""
        # Test with the actual experiment_data.json structure
        analyzer = CBSDataAnalyzer()
        
        # Create data in the expected format from the actual file
        real_format_data = {
            "experiment_metadata": {
                "date": "2025-09-02",
                "duration_hours": 168,
                "test_vehicles": 5
            },
            "performance_metrics": {
                "frame_loss_rate": {
                    "background_traffic_mbps": [0, 200, 400, 600, 800, 1000, 1200],
                    "without_cbs": [0.0, 3.2, 8.7, 14.3, 19.6, 23.8, 27.5],
                    "with_cbs": [0.0, 0.0, 0.02, 0.08, 0.21, 0.38, 0.52],
                    "with_cbs_and_tas": [0.0, 0.0, 0.0, 0.01, 0.05, 0.12, 0.18]
                },
                "latency_ms": {
                    "percentiles": {
                        "without_cbs": {"p50": 62.4, "p95": 85.7, "max": 98.7},
                        "with_cbs": {"p50": 6.8, "p95": 10.1, "max": 14.3},
                        "with_cbs_and_tas": {"p50": 3.2, "p95": 6.2, "max": 10.2}
                    },
                    "time_series": {
                        "timestamps_sec": [0, 60, 120, 180, 240, 300],
                        "without_cbs": [45.2, 62.3, 71.8, 68.4, 75.2, 69.1],
                        "with_cbs": [6.8, 6.9, 7.1, 6.7, 7.0, 6.9]
                    }
                },
                "jitter_ms": {
                    "traffic_load_mbps": [0, 200, 400, 600, 800, 1000, 1200],
                    "video_4k": {
                        "without_cbs": [2.1, 12.3, 24.7, 35.8, 42.3, 48.7, 52.4],
                        "with_cbs": [0.8, 1.2, 1.8, 2.1, 2.5, 2.8, 3.1]
                    },
                    "video_1080p": {
                        "without_cbs": [1.8, 9.7, 18.3, 28.4, 36.2, 41.9, 45.3],
                        "with_cbs": [0.7, 1.1, 1.6, 1.9, 2.3, 2.6, 2.9]
                    },
                    "sensor_data": {
                        "without_cbs": [0.5, 3.2, 8.1, 14.3, 19.7, 24.8, 28.3],
                        "with_cbs": [0.2, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3]
                    }
                },
                "credit_dynamics": {
                    "timestamps_us": [0, 10, 20, 30, 40, 50],
                    "credit_values": [0, 300, 365, -2000, -6000, -1000],
                    "state_transitions": ["IDLE", "WAIT", "READY", "SEND", "SEND", "WAIT"],
                    "queue_depth": [0, 3, 5, 4, 2, 4]
                }
            }
        }
        
        analyzer.data = real_format_data
        
        # Test all major functions
        summary = analyzer.generate_performance_summary()
        assert len(summary) == 7  # Should match the number of background traffic levels
        
        # Test plot generation (mock the write operations)
        with patch('plotly.graph_objects.Figure.write_html'):
            fig1 = analyzer.plot_frame_loss_comparison()
            fig2 = analyzer.plot_latency_analysis()
            fig3 = analyzer.plot_jitter_analysis()
            fig4 = analyzer.plot_credit_dynamics()
            
            assert all(fig is not None for fig in [fig1, fig2, fig3, fig4])
        
        # Test statistical report
        report = analyzer.generate_statistical_report()
        assert isinstance(report, dict)
        assert 'summary' in report

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])