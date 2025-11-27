"""Debugging utilities for analyzing errors and stack traces in Zino."""

import inspect
import logging
from typing import Any, Dict, List, Optional, Type

_log = logging.getLogger(__name__)


def debug_log_timeout_error(device_name: str, task_class: Type, logger: Optional[logging.Logger] = None) -> None:
    """Debug log detailed information about a TimeoutError including stack frame analysis.

    :param device_name: Name of the device that timed out
    :param task_class: The task class that was running when the timeout occurred
    :param logger: Optional logger to use. If omitted, the module level logger will be used
    """
    # Use provided logger or fall back to module-level logger
    log = logger if logger is not None else _log

    frames = inspect.trace()

    # Find and log task-level failure information
    task_frame_info = _find_task_frame(frames)
    if task_frame_info:
        log.debug(
            "%s: TimeoutError in %s.%s at %s:%d:%s",
            device_name,
            task_class.__name__,
            task_frame_info["function"],
            task_frame_info["filename"],
            task_frame_info["lineno"],
            task_frame_info["context"],
        )

    # Extract and log SNMP operation details
    snmp_details = _extract_snmp_operation_details(frames)
    if snmp_details:
        log.debug("%s: SNMP operation failed: %s", device_name, snmp_details)


def _find_task_frame(frames: List[inspect.FrameInfo]) -> Optional[Dict[str, Any]]:
    """Find the lowest level stack frame inside the failing task class."""
    from zino.tasks.task import Task

    for frame_info in reversed(frames):
        frame, filename, lineno, function, code_context, index = frame_info
        if "self" in frame.f_locals:
            obj = frame.f_locals["self"]
            # Check if this is an instance of the base Task class (or any subclass)
            if isinstance(obj, Task):
                return {
                    "filename": filename,
                    "lineno": lineno,
                    "function": function,
                    "context": code_context[index].rstrip() if code_context and index is not None else "no context",
                }
    return None


def _extract_snmp_operation_details(frames: List[inspect.FrameInfo]) -> Optional[str]:
    """Extract details about the SNMP operation that timed out from the stack frames."""
    for frame_info in frames:
        frame = frame_info.frame
        function = frame_info.function

        # Check if this is an SNMP operation frame
        if "self" in frame.f_locals:
            obj = frame.f_locals.get("self")
            # Check if this is an SNMP object
            if obj and type(obj).__name__ == "SNMP":
                return _format_snmp_operation_info(function, frame.f_locals)
    return None


def _format_snmp_operation_info(function: str, locals_dict: Dict[str, Any]) -> str:
    """Format SNMP operation information from function name and local variables."""
    info_parts = []

    # Determine operation type
    if function in ["get", "get2"]:
        info_parts.append("operation=GET")
    elif function in ["getnext", "getnext2"]:
        info_parts.append("operation=GET-NEXT")
    elif function in ["getbulk", "getbulk2", "bulkwalk", "sparsewalk"]:
        info_parts.append("operation=GET-BULK")
    elif function == "walk":
        info_parts.append("operation=WALK (via GET-NEXT)")
    else:
        info_parts.append(f"operation={function}")

    # Add OID/variables information
    if "oid" in locals_dict:
        info_parts.append(f"oid={locals_dict['oid']}")
    elif "variables" in locals_dict:
        info_parts.append(f"variables={locals_dict['variables']}")

    # Add max_repetitions for bulk operations
    if "max_repetitions" in locals_dict:
        info_parts.append(f"max_repetitions={locals_dict['max_repetitions']}")

    return ", ".join(info_parts)
