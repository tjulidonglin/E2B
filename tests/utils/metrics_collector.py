"""
Metrics Collector - Collects resource metrics from E2B sandboxes
"""

import time
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ResourceMetrics:
    """Resource metrics for a sandbox"""
    timestamp: float
    cpu_percent: float
    memory_total_mb: float
    memory_used_mb: float
    memory_available_mb: float
    memory_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_available_gb: float
    disk_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_total_mb": self.memory_total_mb,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "memory_percent": self.memory_percent,
            "disk_total_gb": self.disk_total_gb,
            "disk_used_gb": self.disk_used_gb,
            "disk_available_gb": self.disk_available_gb,
            "disk_percent": self.disk_percent,
        }


class MetricsCollector:
    """
    Collects resource metrics from sandboxes using internal commands.
    
    Metrics collected:
    - CPU usage
    - Memory usage
    - Disk usage
    """
    
    def __init__(self, sandbox):
        """
        Initialize MetricsCollector.
        
        Args:
            sandbox: E2B Sandbox instance
        """
        self.sandbox = sandbox
        self._metrics_history: List[ResourceMetrics] = []
    
    def collect(self) -> ResourceMetrics:
        """
        Collect current resource metrics from sandbox.
        
        Returns:
            ResourceMetrics object with current metrics
        """
        timestamp = time.time()
        
        # Collect CPU usage
        cpu_percent = self._collect_cpu_usage()
        
        # Collect memory info
        mem_info = self._collect_memory_info()
        
        # Collect disk info
        disk_info = self._collect_disk_info()
        
        metrics = ResourceMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_total_mb=mem_info["total_mb"],
            memory_used_mb=mem_info["used_mb"],
            memory_available_mb=mem_info["available_mb"],
            memory_percent=mem_info["percent"],
            disk_total_gb=disk_info["total_gb"],
            disk_used_gb=disk_info["used_gb"],
            disk_available_gb=disk_info["available_gb"],
            disk_percent=disk_info["percent"],
        )
        
        self._metrics_history.append(metrics)
        return metrics
    
    def _collect_cpu_usage(self) -> float:
        """Collect CPU usage percentage"""
        try:
            # Use top command to get CPU usage
            result = self.sandbox.commands.run("top -bn1 | grep 'Cpu(s)' || top -bn1 | grep '%CPU'", timeout=10)
            
            if result.exit_code == 0 and result.stdout:
                # Parse CPU usage from top output
                match = re.search(r'(\d+\.?\d*)\s*[iu]d', result.stdout)
                if match:
                    idle = float(match.group(1))
                    return 100.0 - idle
                
                # Alternative format
                match = re.search(r'(\d+\.?\d*)\s*us', result.stdout)
                if match:
                    return float(match.group(1))
            
            return 0.0
        except Exception:
            return 0.0
    
    def _collect_memory_info(self) -> Dict[str, float]:
        """Collect memory information"""
        try:
            result = self.sandbox.commands.run("cat /proc/meminfo", timeout=10)
            
            if result.exit_code == 0 and result.stdout:
                meminfo = {}
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = int(parts[1].strip().split()[0])
                        meminfo[key] = value
                
                total_kb = meminfo.get("MemTotal", 0)
                available_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
                used_kb = total_kb - available_kb
                percent = (used_kb / total_kb * 100) if total_kb > 0 else 0
                
                return {
                    "total_mb": total_kb / 1024,
                    "used_mb": used_kb / 1024,
                    "available_mb": available_kb / 1024,
                    "percent": percent,
                }
            
            return {"total_mb": 0, "used_mb": 0, "available_mb": 0, "percent": 0}
        except Exception:
            return {"total_mb": 0, "used_mb": 0, "available_mb": 0, "percent": 0}
    
    def _collect_disk_info(self) -> Dict[str, float]:
        """Collect disk information"""
        try:
            result = self.sandbox.commands.run("df -BG /", timeout=10)
            
            if result.exit_code == 0 and result.stdout:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        total_gb = float(parts[1].rstrip('G'))
                        used_gb = float(parts[2].rstrip('G'))
                        available_gb = float(parts[3].rstrip('G'))
                        percent = float(parts[4].rstrip('%'))
                        
                        return {
                            "total_gb": total_gb,
                            "used_gb": used_gb,
                            "available_gb": available_gb,
                            "percent": percent,
                        }
            
            return {"total_gb": 0, "used_gb": 0, "available_gb": 0, "percent": 0}
        except Exception:
            return {"total_gb": 0, "used_gb": 0, "available_gb": 0, "percent": 0}