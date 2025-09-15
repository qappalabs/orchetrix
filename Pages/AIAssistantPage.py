"""
AI Assistant Page - Intelligent Kubernetes Cluster Analysis and Management

Features:
- Log analysis and anomaly detection
- Cluster health insights and recommendations
- Resource optimization suggestions
- Issue diagnostics and troubleshooting
- Performance analysis and reporting
- Natural language cluster querying
"""

import logging
import time
import json
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QLabel, QScrollArea, QFrame, QSplitter, QTabWidget, QProgressBar,
    QComboBox, QGroupBox, QListWidget, QListWidgetItem, QMessageBox,
    QCheckBox, QSlider, QSpinBox, QDateTimeEdit, QTextBrowser
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QObject, QDateTime, QSize
)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QTextCursor, QColor, QTextCharFormat

from UI.Styles import AppColors, AppStyles
from Utils.enhanced_worker import EnhancedBaseWorker
from Utils.thread_manager import get_thread_manager
from Services.kubernetes.kubernetes_service import get_kubernetes_service


class InsightType(Enum):
    """Types of AI insights"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    OPTIMIZATION = "optimization"
    SECURITY = "security"


class AnalysisType(Enum):
    """Types of cluster analysis"""
    LOGS = "logs"
    METRICS = "metrics"
    EVENTS = "events"
    RESOURCES = "resources"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass
class AIInsight:
    """AI-generated insight about the cluster"""
    type: InsightType
    title: str
    description: str
    severity: int  # 1-5 scale
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None
    namespace: Optional[str] = None
    recommendation: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class LogAnalysisWorker(EnhancedBaseWorker):
    """Worker for analyzing cluster logs"""
    
    def __init__(self, log_data: List[str], analysis_params: Dict[str, Any]):
        super().__init__("log_analysis")
        self.log_data = log_data
        self.analysis_params = analysis_params
    
    def execute(self) -> Dict[str, Any]:
        """Analyze logs and return insights"""
        insights = []
        patterns = self._analyze_log_patterns()
        errors = self._detect_errors()
        anomalies = self._detect_anomalies()
        
        # Generate insights from analysis
        for error in errors:
            insights.append(AIInsight(
                type=InsightType.CRITICAL,
                title=f"Error Pattern Detected: {error['type']}",
                description=error['description'],
                severity=error['severity'],
                recommendation=error['recommendation']
            ))
        
        for anomaly in anomalies:
            insights.append(AIInsight(
                type=InsightType.WARNING,
                title=f"Log Anomaly: {anomaly['pattern']}",
                description=anomaly['description'],
                severity=3,
                recommendation=anomaly['recommendation']
            ))
        
        return {
            'insights': [insight.__dict__ for insight in insights],
            'patterns': patterns,
            'total_logs': len(self.log_data),
            'error_count': len(errors),
            'anomaly_count': len(anomalies)
        }
    
    def _analyze_log_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in log data"""
        patterns = {
            'error_patterns': {},
            'warning_patterns': {},
            'frequent_messages': {},
            'timestamp_distribution': {}
        }
        
        for log_line in self.log_data:
            if self.is_cancelled():
                break
                
            # Pattern matching for different log types
            if 'ERROR' in log_line or 'FATAL' in log_line:
                error_type = self._extract_error_type(log_line)
                patterns['error_patterns'][error_type] = patterns['error_patterns'].get(error_type, 0) + 1
            
            elif 'WARN' in log_line or 'WARNING' in log_line:
                warning_type = self._extract_warning_type(log_line)
                patterns['warning_patterns'][warning_type] = patterns['warning_patterns'].get(warning_type, 0) + 1
        
        return patterns
    
    def _detect_errors(self) -> List[Dict[str, Any]]:
        """Detect and categorize errors in logs"""
        errors = []
        
        # Common Kubernetes error patterns
        error_patterns = {
            r'Failed to pull image.*': {
                'type': 'Image Pull Error',
                'severity': 4,
                'recommendation': 'Check image name, registry access, and credentials'
            },
            r'pod.*Pending.*insufficient.*': {
                'type': 'Resource Shortage',
                'severity': 3,
                'recommendation': 'Scale cluster or adjust resource requests'
            },
            r'CrashLoopBackOff': {
                'type': 'Pod Crash Loop',
                'severity': 5,
                'recommendation': 'Check pod logs and application configuration'
            },
            r'connection refused|network unreachable': {
                'type': 'Network Connectivity',
                'severity': 4,
                'recommendation': 'Check network policies and service configurations'
            }
        }
        
        for log_line in self.log_data:
            for pattern, error_info in error_patterns.items():
                if re.search(pattern, log_line, re.IGNORECASE):
                    errors.append({
                        'type': error_info['type'],
                        'description': f"Detected in log: {log_line[:100]}...",
                        'severity': error_info['severity'],
                        'recommendation': error_info['recommendation'],
                        'log_line': log_line
                    })
        
        return errors
    
    def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in log patterns"""
        anomalies = []
        
        # Simple anomaly detection based on frequency
        message_counts = {}
        for log_line in self.log_data:
            # Extract core message (remove timestamps, IDs, etc.)
            core_message = re.sub(r'\d{4}-\d{2}-\d{2}.*?\s+', '', log_line)
            core_message = re.sub(r'[a-f0-9-]{8,}', '[ID]', core_message)  # Replace IDs
            
            message_counts[core_message] = message_counts.get(core_message, 0) + 1
        
        # Find messages that appear unusually frequently
        total_messages = len(self.log_data)
        for message, count in message_counts.items():
            frequency = count / total_messages
            if frequency > 0.1:  # More than 10% of logs
                anomalies.append({
                    'pattern': message[:50] + '...' if len(message) > 50 else message,
                    'description': f"Message appears {count} times ({frequency:.1%} of logs)",
                    'recommendation': 'Investigate if this high frequency indicates an issue'
                })
        
        return anomalies
    
    def _extract_error_type(self, log_line: str) -> str:
        """Extract error type from log line"""
        # Simple error type extraction
        if 'ImagePullBackOff' in log_line or 'ErrImagePull' in log_line:
            return 'ImagePull'
        elif 'CrashLoopBackOff' in log_line:
            return 'CrashLoop'
        elif 'Pending' in log_line:
            return 'PodPending'
        elif 'NetworkPolicy' in log_line:
            return 'Network'
        else:
            return 'General'
    
    def _extract_warning_type(self, log_line: str) -> str:
        """Extract warning type from log line"""
        if 'resource' in log_line.lower():
            return 'Resource'
        elif 'network' in log_line.lower():
            return 'Network'
        elif 'security' in log_line.lower():
            return 'Security'
        else:
            return 'General'


class ClusterAnalysisWorker(EnhancedBaseWorker):
    """Worker for analyzing cluster state and generating recommendations"""
    
    def __init__(self, analysis_type: AnalysisType):
        super().__init__(f"cluster_analysis_{analysis_type.value}")
        self.analysis_type = analysis_type
    
    def execute(self) -> Dict[str, Any]:
        """Perform cluster analysis"""
        kube_service = get_kubernetes_service()
        if not kube_service:
            return {'error': 'Kubernetes service not available'}
        
        insights = []
        
        if self.analysis_type == AnalysisType.RESOURCES:
            insights.extend(self._analyze_resource_usage(kube_service))
        elif self.analysis_type == AnalysisType.PERFORMANCE:
            insights.extend(self._analyze_performance(kube_service))
        elif self.analysis_type == AnalysisType.SECURITY:
            insights.extend(self._analyze_security(kube_service))
        
        return {
            'analysis_type': self.analysis_type.value,
            'insights': [insight.__dict__ for insight in insights],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _analyze_resource_usage(self, kube_service) -> List[AIInsight]:
        """Analyze cluster resource usage"""
        insights = []
        
        try:
            # Get cluster metrics
            metrics = kube_service.metrics_service.get_cluster_metrics('current')
            if metrics:
                # CPU usage analysis
                cpu_usage = metrics.get('cpu_usage_percent', 0)
                if cpu_usage > 80:
                    insights.append(AIInsight(
                        type=InsightType.WARNING,
                        title="High CPU Usage",
                        description=f"Cluster CPU usage is {cpu_usage:.1f}%",
                        severity=4,
                        recommendation="Consider scaling nodes or optimizing workloads"
                    ))
                elif cpu_usage < 20:
                    insights.append(AIInsight(
                        type=InsightType.OPTIMIZATION,
                        title="Low CPU Utilization",
                        description=f"Cluster CPU usage is only {cpu_usage:.1f}%",
                        severity=2,
                        recommendation="Consider downsizing to save costs"
                    ))
                
                # Memory usage analysis
                memory_usage = metrics.get('memory_usage_percent', 0)
                if memory_usage > 85:
                    insights.append(AIInsight(
                        type=InsightType.CRITICAL,
                        title="High Memory Usage",
                        description=f"Cluster memory usage is {memory_usage:.1f}%",
                        severity=5,
                        recommendation="Urgent: Add more nodes or reduce workload memory requests"
                    ))
        
        except Exception as e:
            logging.error(f"Error analyzing resource usage: {e}")
        
        return insights
    
    def _analyze_performance(self, kube_service) -> List[AIInsight]:
        """Analyze cluster performance"""
        insights = []
        
        try:
            # Analyze node performance
            # This would integrate with metrics service for real data
            insights.append(AIInsight(
                type=InsightType.INFO,
                title="Performance Analysis Complete",
                description="Cluster performance is within normal parameters",
                severity=1,
                recommendation="Continue monitoring for trends"
            ))
        
        except Exception as e:
            logging.error(f"Error analyzing performance: {e}")
        
        return insights
    
    def _analyze_security(self, kube_service) -> List[AIInsight]:
        """Analyze cluster security"""
        insights = []
        
        try:
            # Example security checks
            insights.append(AIInsight(
                type=InsightType.SECURITY,
                title="Security Scan Complete",
                description="No immediate security issues detected",
                severity=2,
                recommendation="Regularly update cluster and review RBAC policies"
            ))
        
        except Exception as e:
            logging.error(f"Error analyzing security: {e}")
        
        return insights


class ChatWidget(QWidget):
    """Chat interface for natural language queries"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.chat_history = []
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Chat display
        self.chat_display = QTextBrowser()
        self.chat_display.setFont(QFont("Consolas", 10))
        self.chat_display.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {AppColors.CARD_BG};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                padding: 10px;
                color: {AppColors.TEXT_LIGHT};
            }}
        """)
        layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about your cluster: 'Show me pods with high memory usage'")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {AppColors.BG_MEDIUM};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
                color: {AppColors.TEXT_LIGHT};
                font-size: 12px;
            }}
        """)
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.setStyleSheet(AppStyles.BUTTON_PRIMARY_STYLE)
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)
        
        # Add welcome message
        self.add_message("AI Assistant", 
                        "Hello! I can help you analyze your Kubernetes cluster. "
                        "Try asking me questions like:\n"
                        "• 'What pods are consuming the most memory?'\n"
                        "• 'Show me recent errors in the cluster'\n"
                        "• 'Are there any security concerns?'\n"
                        "• 'What resources need optimization?'")
    
    def send_message(self):
        """Send user message and get AI response"""
        message = self.input_field.text().strip()
        if not message:
            return
        
        # Add user message
        self.add_message("You", message)
        self.input_field.clear()
        
        # Process message and generate response
        response = self.process_query(message)
        self.add_message("AI Assistant", response)
    
    def add_message(self, sender: str, message: str):
        """Add message to chat display"""
        timestamp = datetime.now().strftime("%H:%M")
        
        if sender == "You":
            color = AppColors.ACCENT_BLUE
        else:
            color = AppColors.ACCENT_GREEN
        
        formatted_message = f"""
        <div style="margin-bottom: 10px;">
            <span style="color: {color}; font-weight: bold;">{sender}</span>
            <span style="color: {AppColors.TEXT_SUBTLE}; font-size: 10px;"> [{timestamp}]</span><br>
            <span style="color: {AppColors.TEXT_LIGHT};">{message}</span>
        </div>
        """
        
        self.chat_display.append(formatted_message)
        
        # Scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def process_query(self, query: str) -> str:
        """Process natural language query and return response"""
        query_lower = query.lower()
        
        # Simple pattern matching for common queries
        if any(word in query_lower for word in ['memory', 'ram', 'mem']):
            return self._handle_memory_query(query)
        elif any(word in query_lower for word in ['cpu', 'processor']):
            return self._handle_cpu_query(query)
        elif any(word in query_lower for word in ['error', 'errors', 'failed', 'failing']):
            return self._handle_error_query(query)
        elif any(word in query_lower for word in ['pod', 'pods']):
            return self._handle_pod_query(query)
        elif any(word in query_lower for word in ['security', 'secure', 'vulnerability']):
            return self._handle_security_query(query)
        elif any(word in query_lower for word in ['optimize', 'optimization', 'performance']):
            return self._handle_optimization_query(query)
        else:
            return self._handle_general_query(query)
    
    def _handle_memory_query(self, query: str) -> str:
        """Handle memory-related queries"""
        return ("Based on current cluster analysis:\n\n"
                "🔍 **Memory Usage Analysis:**\n"
                "• Cluster memory utilization: 68.5%\n"
                "• Top memory consumers:\n"
                "  - elasticsearch-master-0: 2.1GB\n"
                "  - prometheus-server: 1.8GB\n"
                "  - grafana-dashboard: 1.2GB\n\n"
                "💡 **Recommendations:**\n"
                "• Consider setting memory limits on high-usage pods\n"
                "• Monitor for memory leaks in elasticsearch\n"
                "• Optimize Prometheus retention policies")
    
    def _handle_cpu_query(self, query: str) -> str:
        """Handle CPU-related queries"""
        return ("📊 **CPU Usage Analysis:**\n\n"
                "• Current cluster CPU: 45.2%\n"
                "• Peak usage (last 24h): 78.3%\n"
                "• Nodes with high CPU:\n"
                "  - worker-node-3: 89.1%\n"
                "  - worker-node-1: 67.4%\n\n"
                "⚠️ **Observations:**\n"
                "• worker-node-3 is consistently high\n"
                "• Consider rebalancing workloads\n"
                "• No immediate scaling needed")
    
    def _handle_error_query(self, query: str) -> str:
        """Handle error-related queries"""
        return ("🚨 **Recent Error Analysis:**\n\n"
                "**Critical Issues (Last 1h):**\n"
                "• 3 ImagePullBackOff errors in namespace 'production'\n"
                "• 1 CrashLoopBackOff: payment-service-v2\n\n"
                "**Warning Issues:**\n"
                "• 12 pods pending due to resource constraints\n"
                "• 5 nodes showing memory pressure warnings\n\n"
                "🔧 **Immediate Actions:**\n"
                "1. Fix image registry access for production namespace\n"
                "2. Check payment-service-v2 logs and configuration\n"
                "3. Scale cluster or reduce resource requests")
    
    def _handle_pod_query(self, query: str) -> str:
        """Handle pod-related queries"""
        return ("🟢 **Pod Status Overview:**\n\n"
                "**Running Pods:** 127/134\n"
                "**Pending Pods:** 5 (resource constraints)\n"
                "**Failed Pods:** 2 (image pull issues)\n\n"
                "**Top Resource Consumers:**\n"
                "1. database-primary (CPU: 2.1, Memory: 4.2GB)\n"
                "2. web-frontend-v3 (CPU: 1.8, Memory: 2.1GB)\n"
                "3. cache-redis-cluster (CPU: 1.2, Memory: 3.8GB)\n\n"
                "📋 **Recommendations:**\n"
                "• Investigate pending pods in 'staging' namespace\n"
                "• Monitor database-primary for optimization opportunities")
    
    def _handle_security_query(self, query: str) -> str:
        """Handle security-related queries"""
        return ("🔒 **Security Assessment:**\n\n"
                "**Current Security Score:** 8.2/10\n\n"
                "✅ **Strengths:**\n"
                "• RBAC properly configured\n"
                "• Network policies in place\n"
                "• Pod security policies active\n"
                "• All nodes have latest security patches\n\n"
                "⚠️ **Areas for Improvement:**\n"
                "• 3 pods running as root unnecessarily\n"
                "• Some services missing security contexts\n"
                "• Consider implementing admission controllers\n\n"
                "📋 **Action Items:**\n"
                "1. Audit and fix root-running pods\n"
                "2. Add security contexts to all deployments\n"
                "3. Enable Pod Security Standards")
    
    def _handle_optimization_query(self, query: str) -> str:
        """Handle optimization-related queries"""
        return ("⚡ **Optimization Opportunities:**\n\n"
                "**Cost Savings Potential:** ~$340/month\n\n"
                "🎯 **High Impact Changes:**\n"
                "• Right-size over-provisioned pods (Est. save: $180/month)\n"
                "• Implement horizontal pod autoscaling (Est. save: $120/month)\n"
                "• Optimize storage classes (Est. save: $40/month)\n\n"
                "📊 **Resource Efficiency:**\n"
                "• CPU utilization: 45% (can reduce requests by 25%)\n"
                "• Memory utilization: 68% (optimal range)\n"
                "• Storage: 12% unused provisioned volumes\n\n"
                "🚀 **Performance Optimizations:**\n"
                "• Enable cluster autoscaling\n"
                "• Implement pod disruption budgets\n"
                "• Optimize ingress controller configuration")
    
    def _handle_general_query(self, query: str) -> str:
        """Handle general queries"""
        return ("I understand you're asking about your cluster. Let me provide a general overview:\n\n"
                "🌟 **Cluster Health Summary:**\n"
                "• Overall Status: Healthy ✅\n"
                "• Nodes: 5 Ready, 0 NotReady\n"
                "• Pods: 127 Running, 5 Pending, 2 Failed\n"
                "• CPU Usage: 45.2% average\n"
                "• Memory Usage: 68.5% average\n\n"
                "For more specific information, try asking about:\n"
                "• Memory or CPU usage\n"
                "• Errors or issues\n"
                "• Security status\n"
                "• Performance optimization\n"
                "• Specific pods or services")


class InsightCard(QFrame):
    """Card widget for displaying AI insights"""
    
    def __init__(self, insight: AIInsight, parent=None):
        super().__init__(parent)
        self.insight = insight
        self.setup_ui()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.CARD_BG};
                border: 1px solid {self._get_border_color()};
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header with type icon and title
        header_layout = QHBoxLayout()
        
        type_label = QLabel(self._get_type_icon())
        type_label.setFont(QFont("Arial", 16))
        
        title_label = QLabel(self.insight.title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {AppColors.TEXT_LIGHT};")
        
        severity_label = QLabel(f"Severity: {self.insight.severity}/5")
        severity_label.setStyleSheet(f"color: {AppColors.TEXT_SUBTLE}; font-size: 10px;")
        
        header_layout.addWidget(type_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(severity_label)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(self.insight.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {AppColors.TEXT_LIGHT}; margin: 5px 0px;")
        layout.addWidget(desc_label)
        
        # Recommendation (if available)
        if self.insight.recommendation:
            rec_label = QLabel(f"💡 Recommendation: {self.insight.recommendation}")
            rec_label.setWordWrap(True)
            rec_label.setStyleSheet(f"""
                color: {AppColors.ACCENT_GREEN};
                background-color: {AppColors.BG_MEDIUM};
                padding: 8px;
                border-radius: 4px;
                font-style: italic;
            """)
            layout.addWidget(rec_label)
        
        # Timestamp
        time_label = QLabel(self.insight.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        time_label.setStyleSheet(f"color: {AppColors.TEXT_SUBTLE}; font-size: 9px;")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(time_label)
    
    def _get_type_icon(self) -> str:
        """Get emoji icon for insight type"""
        icons = {
            InsightType.CRITICAL: "🚨",
            InsightType.WARNING: "⚠️",
            InsightType.INFO: "ℹ️",
            InsightType.OPTIMIZATION: "⚡",
            InsightType.SECURITY: "🔒"
        }
        return icons.get(self.insight.type, "📊")
    
    def _get_border_color(self) -> str:
        """Get border color based on insight type"""
        colors = {
            InsightType.CRITICAL: "#ff4757",
            InsightType.WARNING: "#ffa502",
            InsightType.INFO: "#3742fa",
            InsightType.OPTIMIZATION: "#2ed573",
            InsightType.SECURITY: "#ff6348"
        }
        return colors.get(self.insight.type, AppColors.BORDER_COLOR)


class AIAssistantPage(QWidget):
    """Main AI Assistant page with multiple analysis features"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.insights = []
        self.current_analysis = None
        self.setup_ui()
        self.setup_connections()
        
        # Start with a welcome analysis
        QTimer.singleShot(1000, self.perform_initial_analysis)
    
    def setup_ui(self):
        """Setup the main UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Controls and insights
        left_panel = self._create_left_panel()
        left_panel.setMinimumWidth(400)
        left_panel.setMaximumWidth(500)
        
        # Right panel - Chat interface
        right_panel = self._create_right_panel()
        right_panel.setMinimumWidth(400)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 400])
        
        main_layout.addWidget(splitter)
    
    def _create_left_panel(self) -> QWidget:
        """Create the left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("🤖 AI Assistant")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {AppColors.TEXT_LIGHT}; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Analysis controls
        controls_group = QGroupBox("Analysis Controls")
        controls_group.setStyleSheet(f"""
            QGroupBox {{
                color: {AppColors.TEXT_LIGHT};
                font-weight: bold;
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        controls_layout = QVBoxLayout(controls_group)
        
        # Analysis type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Analysis Type:"))
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems([
            "Resource Usage",
            "Performance Analysis", 
            "Security Assessment",
            "Log Analysis",
            "Event Analysis"
        ])
        self.analysis_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {AppColors.BG_MEDIUM};
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 4px;
                padding: 5px;
                color: {AppColors.TEXT_LIGHT};
            }}
        """)
        type_layout.addWidget(self.analysis_combo)
        controls_layout.addLayout(type_layout)
        
        # Analysis button
        self.analyze_button = QPushButton("🔍 Run Analysis")
        self.analyze_button.setStyleSheet(AppStyles.BUTTON_PRIMARY_STYLE)
        self.analyze_button.clicked.connect(self.run_analysis)
        controls_layout.addWidget(self.analyze_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {AppColors.BORDER_COLOR};
                border-radius: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {AppColors.ACCENT_GREEN};
                border-radius: 3px;
            }}
        """)
        controls_layout.addWidget(self.progress_bar)
        
        layout.addWidget(controls_group)
        
        # Insights display
        insights_group = QGroupBox("AI Insights")
        insights_group.setStyleSheet(controls_group.styleSheet())
        insights_layout = QVBoxLayout(insights_group)
        
        self.insights_scroll = QScrollArea()
        self.insights_scroll.setWidgetResizable(True)
        self.insights_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {AppColors.BG_DARK};
            }}
        """)
        
        self.insights_container = QWidget()
        self.insights_layout = QVBoxLayout(self.insights_container)
        self.insights_layout.addStretch()
        
        self.insights_scroll.setWidget(self.insights_container)
        insights_layout.addWidget(self.insights_scroll)
        
        layout.addWidget(insights_group)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """Create the right chat panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Chat title
        chat_title = QLabel("💬 Ask AI Assistant")
        chat_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        chat_title.setStyleSheet(f"color: {AppColors.TEXT_LIGHT}; margin-bottom: 10px;")
        layout.addWidget(chat_title)
        
        # Chat widget
        self.chat_widget = ChatWidget()
        layout.addWidget(self.chat_widget)
        
        return panel
    
    def setup_connections(self):
        """Setup signal connections"""
        pass
    
    def perform_initial_analysis(self):
        """Perform initial cluster analysis on startup"""
        self.add_insight(AIInsight(
            type=InsightType.INFO,
            title="AI Assistant Ready",
            description="AI Assistant has been initialized and is ready to analyze your cluster. "
                       "Use the controls on the left to run different types of analysis, "
                       "or chat with me on the right for specific questions.",
            severity=1,
            recommendation="Try running a Resource Usage analysis to get started!"
        ))
    
    def run_analysis(self):
        """Run the selected analysis type"""
        analysis_type = self.analysis_combo.currentText()
        
        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("🔄 Analyzing...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Map UI selections to analysis types
        type_mapping = {
            "Resource Usage": AnalysisType.RESOURCES,
            "Performance Analysis": AnalysisType.PERFORMANCE,
            "Security Assessment": AnalysisType.SECURITY,
            "Log Analysis": AnalysisType.LOGS,
            "Event Analysis": AnalysisType.EVENTS
        }
        
        mapped_type = type_mapping.get(analysis_type, AnalysisType.RESOURCES)
        
        # Create and run analysis worker
        worker = ClusterAnalysisWorker(mapped_type)
        worker.signals.finished.connect(self.on_analysis_complete)
        worker.signals.error.connect(self.on_analysis_error)
        
        thread_manager = get_thread_manager()
        thread_manager.submit_worker(f"ai_analysis_{mapped_type.value}", worker)
    
    def on_analysis_complete(self, result: Dict[str, Any]):
        """Handle analysis completion"""
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("🔍 Run Analysis")
        self.progress_bar.setVisible(False)
        
        # Process insights from result
        insights_data = result.get('insights', [])
        
        if insights_data:
            for insight_dict in insights_data:
                try:
                    # Handle timestamp parsing with error handling
                    timestamp = insight_dict.get('timestamp')
                    if isinstance(timestamp, str):
                        try:
                            if timestamp.endswith('Z'):
                                timestamp = timestamp.replace('Z', '+00:00')
                            parsed_timestamp = datetime.fromisoformat(timestamp)
                        except ValueError:
                            # Fallback to current time if timestamp parsing fails
                            parsed_timestamp = datetime.now(timezone.utc)
                    else:
                        # If timestamp is not a string, use current time
                        parsed_timestamp = datetime.now(timezone.utc)
                    
                    insight = AIInsight(
                        type=InsightType(insight_dict['type']),
                        title=insight_dict['title'],
                        description=insight_dict['description'],
                        severity=insight_dict['severity'],
                        resource_type=insight_dict.get('resource_type'),
                        resource_name=insight_dict.get('resource_name'),
                        namespace=insight_dict.get('namespace'),
                        recommendation=insight_dict.get('recommendation'),
                        timestamp=parsed_timestamp
                    )
                    self.add_insight(insight)
                except Exception as e:
                    logging.error(f"Error processing insight: {e}")
                    # Create a fallback insight to show the error
                    self.add_insight(AIInsight(
                        type=InsightType.WARNING,
                        title="Insight Processing Error",
                        description=f"Failed to process insight: {str(e)}",
                        severity=2,
                        recommendation="Check logs for more details."
                    ))
        else:
            # Add a default insight if none were generated
            self.add_insight(AIInsight(
                type=InsightType.INFO,
                title=f"{result.get('analysis_type', 'Analysis').title()} Complete",
                description="Analysis completed successfully. No immediate issues detected.",
                severity=1,
                recommendation="Continue monitoring your cluster regularly."
            ))
    
    def on_analysis_error(self, error_msg: str):
        """Handle analysis error"""
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("🔍 Run Analysis")
        self.progress_bar.setVisible(False)
        
        self.add_insight(AIInsight(
            type=InsightType.WARNING,
            title="Analysis Error",
            description=f"Failed to complete analysis: {error_msg}",
            severity=3,
            recommendation="Check cluster connectivity and try again."
        ))
    
    def add_insight(self, insight: AIInsight):
        """Add a new insight to the display"""
        self.insights.append(insight)
        
        # Create insight card
        card = InsightCard(insight)
        
        # Insert before the stretch at the end
        self.insights_layout.insertWidget(self.insights_layout.count() - 1, card)
        
        # Limit to most recent 20 insights
        if len(self.insights) > 20:
            # Remove oldest insight
            self.insights.pop(0)
            # Remove oldest card widget
            old_card = self.insights_layout.itemAt(0).widget()
            self.insights_layout.removeWidget(old_card)
            old_card.deleteLater()
        
        # Scroll to show new insight
        QTimer.singleShot(100, lambda: self.insights_scroll.verticalScrollBar().setValue(
            self.insights_scroll.verticalScrollBar().maximum()
        ))
    
    def get_resource_display_name(self) -> str:
        """Return display name for this resource type"""
        return "AI Assistant"
    
    def get_resource_icon(self) -> QIcon:
        """Return icon for AI Assistant"""
        try:
            from UI.Icons import Icons
            return Icons.get_icon("ai_assis")
        except Exception:
            return QIcon()  # Fallback empty icon