import base64
import logging
from typing import List, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


class SandboxExecutor:
    """
    Executes code in a secure, isolated Docker container.
    """

    def __init__(
        self,
        image: str | None = None,
        mem_limit_mb: int | None = None,
        cpu_quota: int | None = None,
    ):
        self.image = image or settings.SANDBOX_DOCKER_IMAGE
        mem_mb = mem_limit_mb if mem_limit_mb is not None else settings.SANDBOX_MEM_LIMIT_MB
        self.mem_limit = f"{int(mem_mb)}m"
        cpu_limit = float(settings.SANDBOX_CPU_LIMIT)
        self.cpu_quota = cpu_quota if cpu_quota is not None else max(1000, int(cpu_limit * 100000))

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

    def run_code(self, code: str, timeout_seconds: int | None = None) -> Tuple[str, str]:
        """
        Runs code in the sandbox.
        Returns (stdout, stderr).
        """
        try:
            import docker
            from docker.errors import APIError, ContainerError, ImageNotFound

            client = docker.from_env()
            effective_timeout = (
                int(timeout_seconds)
                if timeout_seconds is not None
                else int(settings.SANDBOX_TIMEOUT_SECONDS)
            )
            cmd = self._build_command_for_code(code)

            try:
                # Run container detached to control timeout
                container = client.containers.run(
                    image=self.image,
                    command=cmd,
                    remove=False,  # Don't remove immediately so we can get logs
                    network_mode="none",
                    mem_limit=self.mem_limit,
                    cpu_quota=self.cpu_quota,  # Restrict CPU usage
                    stderr=True,
                    stdout=True,
                    detach=True,
                )

                try:
                    # Wait for container to finish with timeout
                    result = container.wait(timeout=effective_timeout)
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
                return self.run_code(code, timeout_seconds)  # Retry once

            except APIError as e:
                return (
                    "",
                    f"Docker API error: {e.explanation if hasattr(e, 'explanation') else str(e)}",
                )

        except ImportError:
            return "", "Docker SDK not installed."
        except Exception as e:
            return "", f"Sandbox execution error: {str(e)}"


# Singleton instance
sandbox = SandboxExecutor()
