"""
JanusLab: Self-Testing Instance Manager

Allows Janus Prime to spawn a lightweight "Lab" instance for testing:
- Code changes before applying
- New tools before registering
- Configuration changes before deploying

The Lab runs in an isolated Docker container with resource limits.
"""

import logging
import json
import os
import time
import tempfile
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None

logger = logging.getLogger(__name__)


@dataclass
class LabConfig:
    """Configuration for a Lab instance."""
    lab_id: str
    purpose: str  # "test_tool", "test_code_change", "benchmark"
    timeout_seconds: int = 300  # 5 minutes max
    cpu_limit: str = "1.0"  # 1 CPU
    memory_limit: str = "2g"  # 2GB RAM
    port: int = 8001  # Different port than Prime
    

@dataclass
class LabResult:
    """Result from a Lab test run."""
    lab_id: str
    success: bool
    duration_seconds: float
    test_output: str
    metrics: Dict[str, Any]
    error: Optional[str] = None


class JanusLabManager:
    """
    Manages Janus Lab instances for safe self-testing.
    
    Janus Prime can:
    1. Spawn a Lab container
    2. Apply proposed changes to Lab
    3. Run tests in Lab
    4. Compare results
    5. Decide to merge or discard
    """
    
    LAB_IMAGE = "janus-completo-janus-api:latest"  # Match docker-compose image name
    LAB_NETWORK = "janus-completo_janus-net"  # Match docker-compose network name
    LAB_PREFIX = "janus_lab_"
    
    def __init__(self):
        if not DOCKER_AVAILABLE:
            raise RuntimeError("Docker SDK not available. Install with: pip install docker")
        
        try:
            self.client = docker.from_env()
            # Verify connection
            self.client.ping()
            logger.info("[JanusLab] Docker client initialized successfully")
        except Exception as e:
            logger.error(f"[JanusLab] Failed to connect to Docker: {e}")
            raise
        
        self._active_labs: Dict[str, Any] = {}

    def spawn_lab(
        self,
        purpose: str,
        code_patch: Optional[str] = None,
        custom_env: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 300
    ) -> LabConfig:
        """
        Spawn a new Lab instance.
        
        Args:
            purpose: What this lab is testing
            code_patch: Optional code to inject/test
            custom_env: Custom environment variables
            timeout_seconds: Max time before auto-kill
            
        Returns:
            LabConfig with details about the spawned lab
        """
        import uuid
        
        lab_id = f"{self.LAB_PREFIX}{uuid.uuid4().hex[:8]}"
        config = LabConfig(
            lab_id=lab_id,
            purpose=purpose,
            timeout_seconds=timeout_seconds
        )
        
        logger.info(f"[JanusLab] Spawning lab: {lab_id} for '{purpose}'")
        
        try:
            # Generate minimal .env for Lab
            lab_env = self._generate_lab_env(custom_env)
            
            # Create temp directory for lab workspace
            lab_workspace = tempfile.mkdtemp(prefix=f"{lab_id}_")
            
            # Write .env file
            env_path = os.path.join(lab_workspace, ".env")
            with open(env_path, "w") as f:
                for key, value in lab_env.items():
                    f.write(f"{key}={value}\n")
            
            # If there's a code patch, write it
            if code_patch:
                patch_path = os.path.join(lab_workspace, "patch.py")
                with open(patch_path, "w") as f:
                    f.write(code_patch)
            
            # Spawn container
            container = self.client.containers.run(
                image=self.LAB_IMAGE,
                name=lab_id,
                detach=True,
                network=self.LAB_NETWORK,
                environment=lab_env,
                volumes={
                    lab_workspace: {"bind": "/app/lab_workspace", "mode": "rw"}
                },
                command=["sh", "-c", "sleep infinity"],  # Keep alive for commands
                cpu_period=100000,
                cpu_quota=int(float(config.cpu_limit) * 100000),
                mem_limit=config.memory_limit,
                labels={
                    "janus.lab": "true",
                    "janus.purpose": purpose,
                    "janus.created": datetime.now().isoformat()
                }
            )
            
            self._active_labs[lab_id] = {
                "container": container,
                "config": config,
                "workspace": lab_workspace,
                "created_at": time.time()
            }
            
            logger.info(f"[JanusLab] Lab {lab_id} spawned successfully")
            return config
            
        except Exception as e:
            logger.error(f"[JanusLab] Failed to spawn lab: {e}", exc_info=True)
            raise

    def run_test_in_lab(
        self,
        lab_id: str,
        test_command: str,
        timeout: int = 60
    ) -> LabResult:
        """
        Execute a test command in the Lab.
        
        Args:
            lab_id: ID of the lab to use
            test_command: Command to run (e.g., "pytest tests/")
            timeout: Command timeout
            
        Returns:
            LabResult with test output and metrics
        """
        if lab_id not in self._active_labs:
            raise ValueError(f"Lab {lab_id} not found")
        
        lab = self._active_labs[lab_id]
        container = lab["container"]
        start_time = time.time()
        
        logger.info(f"[JanusLab] Running test in {lab_id}: {test_command}")
        
        try:
            # Execute command in container
            exec_result = container.exec_run(
                cmd=["sh", "-c", test_command],
                workdir="/app",
                environment={"PYTHONPATH": "/app"}
            )
            
            duration = time.time() - start_time
            output = exec_result.output.decode("utf-8", errors="replace")
            exit_code = exec_result.exit_code
            
            result = LabResult(
                lab_id=lab_id,
                success=(exit_code == 0),
                duration_seconds=duration,
                test_output=output[-5000:],  # Last 5000 chars
                metrics={
                    "exit_code": exit_code,
                    "duration_seconds": duration
                },
                error=None if exit_code == 0 else f"Exit code: {exit_code}"
            )
            
            logger.info(
                f"[JanusLab] Test in {lab_id} {'PASSED' if result.success else 'FAILED'} "
                f"(duration: {duration:.2f}s)"
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[JanusLab] Test execution failed: {e}")
            return LabResult(
                lab_id=lab_id,
                success=False,
                duration_seconds=duration,
                test_output="",
                metrics={},
                error=str(e)
            )

    def run_python_in_lab(
        self,
        lab_id: str,
        python_code: str
    ) -> LabResult:
        """
        Execute Python code in the Lab.
        
        Args:
            lab_id: ID of the lab to use
            python_code: Python code to execute
            
        Returns:
            LabResult with execution output
        """
        # Write code to temp file and run
        escaped_code = python_code.replace("'", "'\\''")
        command = f"python3 -c '{escaped_code}'"
        return self.run_test_in_lab(lab_id, command)

    def destroy_lab(self, lab_id: str, force: bool = True) -> bool:
        """
        Destroy a Lab instance.
        
        Args:
            lab_id: ID of the lab to destroy
            force: Force kill if running
            
        Returns:
            True if destroyed successfully
        """
        if lab_id not in self._active_labs:
            logger.warning(f"[JanusLab] Lab {lab_id} not found")
            return False
        
        lab = self._active_labs[lab_id]
        container = lab["container"]
        workspace = lab["workspace"]
        
        try:
            logger.info(f"[JanusLab] Destroying lab: {lab_id}")
            
            # Stop and remove container
            container.stop(timeout=5)
            container.remove(force=force)
            
            # Clean up workspace
            import shutil
            if os.path.exists(workspace):
                shutil.rmtree(workspace)
            
            del self._active_labs[lab_id]
            logger.info(f"[JanusLab] Lab {lab_id} destroyed")
            return True
            
        except Exception as e:
            logger.error(f"[JanusLab] Failed to destroy lab: {e}")
            return False

    def cleanup_stale_labs(self, max_age_seconds: int = 600) -> int:
        """
        Clean up labs that have been running too long.
        
        Args:
            max_age_seconds: Max age before cleanup
            
        Returns:
            Number of labs cleaned up
        """
        now = time.time()
        stale_labs = []
        
        for lab_id, lab in self._active_labs.items():
            age = now - lab["created_at"]
            if age > max_age_seconds:
                stale_labs.append(lab_id)
        
        cleaned = 0
        for lab_id in stale_labs:
            if self.destroy_lab(lab_id):
                cleaned += 1
        
        if cleaned:
            logger.info(f"[JanusLab] Cleaned up {cleaned} stale labs")
        
        return cleaned

    def list_active_labs(self) -> List[Dict[str, Any]]:
        """List all active Lab instances."""
        result = []
        for lab_id, lab in self._active_labs.items():
            result.append({
                "lab_id": lab_id,
                "purpose": lab["config"].purpose,
                "age_seconds": time.time() - lab["created_at"],
                "timeout": lab["config"].timeout_seconds
            })
        return result

    def _generate_lab_env(self, custom_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate minimal .env for Lab instance."""
        # Base minimal config - Lab uses same infra but isolated
        env = {
            "APP_NAME": "JanusLab",
            "ENVIRONMENT": "lab",
            "DEBUG": "false",
            "LOG_LEVEL": "WARNING",
            
            # Use same databases (read-only preferred)
            "QDRANT_HOST": "janus_qdrant",
            "QDRANT_PORT": "6333",
            "NEO4J_URI": "bolt://janus_neo4j:7687",
            "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
            "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "password"),
            
            # Disable features that could cause side effects
            "DISABLE_WORKERS": "true",
            "DISABLE_SCHEDULER": "true",
            "DISABLE_MEMORY_WRITES": "true",  # Read-only memory
            
            # Use Ollama for LLM (local, no API costs)
            "LLM_DEFAULT_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://janus_ollama:11434",
            "OLLAMA_ORCHESTRATOR_MODEL": "qwen2.5:14b",
        }
        
        # Apply custom overrides
        if custom_env:
            env.update(custom_env)
        
        return env


# Convenience function
def quick_lab_test(code: str, purpose: str = "quick_test") -> LabResult:
    """
    Quick helper to spawn a lab, run code, and cleanup.
    
    Usage:
        result = quick_lab_test("print('Hello from Lab!')")
        print(result.test_output)
    """
    manager = JanusLabManager()
    config = manager.spawn_lab(purpose=purpose)
    
    try:
        result = manager.run_python_in_lab(config.lab_id, code)
        return result
    finally:
        manager.destroy_lab(config.lab_id)
