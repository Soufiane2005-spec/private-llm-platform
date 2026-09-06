"""Runtime resource monitoring implementation."""

import shutil
import subprocess

import psutil

from application.ports.resource_monitor import ResourceMonitor
from domain.models.llm_engine import LLMEngine
from domain.models.resources import (
    EngineRuntimeState,
    EngineRuntimeStatus,
    SystemResourceUsage,
)


class SystemResourceProvider(ResourceMonitor):
    """Collect runtime resource information."""

    def get_system_usage(self) -> SystemResourceUsage:
        """Return current system usage."""

        memory = psutil.virtual_memory()
        gpu = self._get_gpu_usage()

        return SystemResourceUsage(
            cpu_percent=psutil.cpu_percent(),
            memory_percent=memory.percent,
            memory_used_bytes=memory.used,
            memory_total_bytes=memory.total,
            gpu_percent=gpu[0],
            gpu_memory_used_bytes=gpu[1],
            gpu_memory_total_bytes=gpu[2],
        )

    def get_engine_statuses(self) -> tuple[EngineRuntimeStatus, ...]:
        """Return the runtime status of the configured engines."""

        return (
            EngineRuntimeStatus(
                engine=LLMEngine.OLLAMA,
                state=EngineRuntimeState.UNKNOWN,
            ),
            EngineRuntimeStatus(
                engine=LLMEngine.VLLM,
                state=EngineRuntimeState.UNKNOWN,
            ),
        )

    @staticmethod
    def _get_gpu_usage() -> tuple[float | None, int | None, int | None]:
        nvidia_smi = shutil.which("nvidia-smi") or shutil.which("nvidia-smi.exe")

        if nvidia_smi is None:
            return None, None, None

        try:
            completed = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError):
            return None, None, None

        first_line = completed.stdout.strip().splitlines()[0:1]
        if not first_line:
            return None, None, None

        parts = [part.strip() for part in first_line[0].split(",")]
        if len(parts) != 3:
            return None, None, None

        try:
            gpu_percent = float(parts[0])
            memory_used_bytes = int(parts[1]) * 1024 * 1024
            memory_total_bytes = int(parts[2]) * 1024 * 1024
        except ValueError:
            return None, None, None

        return gpu_percent, memory_used_bytes, memory_total_bytes
