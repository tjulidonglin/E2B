"""
Sandbox Manager - Manages E2B sandbox lifecycle for testing
"""

import os
import time
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    raise ImportError("e2b_code_interpreter is required. Install with: pip install e2b_code_interpreter")


@dataclass
class SandboxInfo:
    """Information about a sandbox instance"""
    sandbox_id: str
    template: str
    created_at: float
    killed_at: Optional[float] = None
    create_duration: Optional[float] = None
    status: str = "created"


class SandboxManager:
    """
    Manages sandbox lifecycle for testing purposes.
    
    Features:
    - Create and manage multiple sandboxes
    - Concurrent sandbox creation
    - Automatic cleanup
    - Resource tracking
    """
    
    def __init__(
        self,
        template: Optional[str] = None,
        api_key: Optional[str] = None,
        auto_cleanup: bool = True
    ):
        """
        Initialize SandboxManager.
        
        Args:
            template: Sandbox template ID (defaults to CUBE_TEMPLATE_ID env var)
            api_key: E2B API key (defaults to E2B_API_KEY env var)
            auto_cleanup: Automatically cleanup sandboxes on context exit
        """
        self.template = template or os.environ.get("CUBE_TEMPLATE_ID")
        self.api_key = api_key or os.environ.get("E2B_API_KEY")
        self.auto_cleanup = auto_cleanup
        
        self._sandboxes: List[SandboxInfo] = []
        self._active_sandboxes: Dict[str, Any] = {}
    
    def create_sandbox(
        self,
        template: Optional[str] = None,
        timeout: int = 60
    ) -> tuple[Sandbox, SandboxInfo]:
        """
        Create a single sandbox instance.
        
        Args:
            template: Override default template
            timeout: Timeout for sandbox creation
            
        Returns:
            Tuple of (Sandbox instance, SandboxInfo)
        """
        template = template or self.template
        if not template:
            raise ValueError("Template ID is required. Set CUBE_TEMPLATE_ID or pass template parameter.")
        
        start_time = time.perf_counter()
        sandbox = Sandbox.create(template=template, api_key=self.api_key, timeout=timeout)
        create_duration = time.perf_counter() - start_time
        
        info = SandboxInfo(
            sandbox_id=sandbox.sandbox_id,
            template=template,
            created_at=time.time(),
            create_duration=create_duration,
            status="running"
        )
        
        self._sandboxes.append(info)
        self._active_sandboxes[sandbox.sandbox_id] = sandbox
        
        return sandbox, info
    
    def create_sandboxes_concurrent(
        self,
        count: int,
        template: Optional[str] = None,
        timeout: int = 60,
        max_workers: Optional[int] = None
    ) -> tuple[List[Sandbox], List[SandboxInfo], List[Exception]]:
        """
        Create multiple sandboxes concurrently.
        
        Args:
            count: Number of sandboxes to create
            template: Sandbox template
            timeout: Timeout for each sandbox creation
            max_workers: Maximum concurrent workers (defaults to count)
            
        Returns:
            Tuple of (successful sandboxes, info list, error list)
        """
        max_workers = max_workers or count
        template = template or self.template
        
        sandboxes = []
        infos = []
        errors = []
        
        def _create_one(idx: int):
            try:
                return self.create_sandbox(template=template, timeout=timeout)
            except Exception as e:
                return e
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_create_one, i): i for i in range(count)}
            
            for future in as_completed(futures):
                result = future.result()
                if isinstance(result, Exception):
                    errors.append(result)
                else:
                    sandbox, info = result
                    sandboxes.append(sandbox)
                    infos.append(info)
        
        return sandboxes, infos, errors
    
    def kill_sandbox(self, sandbox_id: str) -> bool:
        """
        Kill a specific sandbox by ID.
        
        Args:
            sandbox_id: Sandbox ID to kill
            
        Returns:
            True if killed successfully, False otherwise
        """
        if sandbox_id not in self._active_sandboxes:
            return False
        
        try:
            sandbox = self._active_sandboxes[sandbox_id]
            sandbox.kill()
            
            # Update info
            for info in self._sandboxes:
                if info.sandbox_id == sandbox_id:
                    info.killed_at = time.time()
                    info.status = "killed"
                    break
            
            del self._active_sandboxes[sandbox_id]
            return True
        except Exception:
            return False
    
    def kill_all(self) -> int:
        """
        Kill all active sandboxes.
        
        Returns:
            Number of sandboxes successfully killed
        """
        killed_count = 0
        sandbox_ids = list(self._active_sandboxes.keys())
        
        for sandbox_id in sandbox_ids:
            if self.kill_sandbox(sandbox_id):
                killed_count += 1
        
        return killed_count
    
    def get_active_count(self) -> int:
        """Get number of active sandboxes"""
        return len(self._active_sandboxes)
    
    def get_sandbox(self, sandbox_id: str) -> Optional[Sandbox]:
        """Get sandbox instance by ID"""
        return self._active_sandboxes.get(sandbox_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about sandbox management"""
        total = len(self._sandboxes)
        active = len(self._active_sandboxes)
        killed = sum(1 for info in self._sandboxes if info.status == "killed")
        
        create_times = [info.create_duration for info in self._sandboxes if info.create_duration]
        
        stats = {
            "total_created": total,
            "active": active,
            "killed": killed,
            "avg_create_time": sum(create_times) / len(create_times) if create_times else 0,
            "min_create_time": min(create_times) if create_times else 0,
            "max_create_time": max(create_times) if create_times else 0,
        }
        
        return stats
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.auto_cleanup:
            self.kill_all()
        return False