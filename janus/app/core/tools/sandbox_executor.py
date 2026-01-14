import base64
import logging
from typing import List, Dict, Any, Tuple

from app.core.infrastructure.message_broker import get_broker
from app.models.schemas import QueueName, TaskMessage, TaskState

logger = logging.getLogger(__name__)

class SandboxExecutor:
    """
    Executes code in a secure, isolated Docker container.
    """
    
    def __init__(self, image: str = "python:3.11-slim", mem_limit: str = "256m", cpu_quota: int = 100000):
        self.image = image
        self.mem_limit = mem_limit
        self.cpu_quota = cpu_quota # 100000 microseconds = 100ms per 100ms period = 1 CPU core roughly

    def _build_command_for_code(self, code: str) -> List[str]:
        """
        Builds a command to execute python code safely inside container.
        Uses base64 encoding to avoid shell escaping issues.
        """
        encoded = base64.b64encode(code.encode("utf-8")).decode("ascii")
        py = (
            "import base64,sys;"
            "code = base64.b64decode('" + encoded + "').decode('utf-8');"
            "globals_dict={'__name__':'__main__'};"
            "exec(code, globals_dict)"
        )
        return ["python", "-c", py]

    def run_code(self, code: str, timeout_seconds: int = 10) -> Tuple[str, str]:
        """
        Runs code in the sandbox.
        Returns (stdout, stderr).
        """
        try:
            from docker.errors import APIError, ContainerError, ImageNotFound
            import docker
            
            client = docker.from_env()
            cmd = self._build_command_for_code(code)
            
            try:
                # Run container detached to control timeout
                container = client.containers.run(
                    image=self.image,
                    command=cmd,
                    remove=False, # Don't remove immediately so we can get logs
                    network_mode="none",
                    mem_limit=self.mem_limit,
                    cpu_quota=self.cpu_quota, # Restrict CPU usage
                    stderr=True,
                    stdout=True,
                    detach=True,
                )
                
                try:
                    # Wait for container to finish with timeout
                    result = container.wait(timeout=timeout_seconds)
                    exit_code = result.get("StatusCode", 0)
                    
                    logs = container.logs(stdout=True, stderr=True)
                    stdout = (
                        logs.decode("utf-8", errors="replace")
                        if isinstance(logs, (bytes, bytearray))
                        else str(logs)
                    )
                    
                    if exit_code != 0:
                        return "", f"Process exited with code {exit_code}. Output: {stdout}"
                        
                    return stdout, ""
                    
                except Exception as e:
                    # Timeout or other error during wait
                    try:
                        container.kill()
                    except Exception:
                        pass
                    return "", f"Execution timed out or failed: {str(e)}"
                finally:
                    # Always remove container
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass
                
            except ImageNotFound:
                # Fallback: pull image and retry
                logger.info(f"Image {self.image} not found, pulling...")
                client.images.pull(self.image)
                return self.run_code(code, timeout_seconds) # Retry once
                
            except APIError as e:
                return "", f"Docker API error: {e.explanation if hasattr(e, 'explanation') else str(e)}"
                
        except ImportError:
            return "", "Docker SDK not installed."
        except Exception as e:
            return "", f"Sandbox execution error: {str(e)}"

# Singleton instance
sandbox = SandboxExecutor()
