"""Preserve browser command failures in jupyter-ai-tools notebook readers."""

from functools import wraps


def configure_notebook_read_errors():
    """Guard the live-model response before jupyter-ai-tools indexes content.

    Keep the existing live/RTC read paths: falling back to disk could return
    stale cells when the browser has unsaved edits.
    """
    from jupyter_ai_tools.toolkits import notebook

    current = notebook.run_lab_command
    if getattr(current, '_flinc_content_guard', False):
        return

    @wraps(current)
    async def run_lab_command(command_id, *args, **kwargs):
        response = await current(command_id, *args, **kwargs)
        if command_id == 'jupyterlab-ai-commands:get-notebook-content':
            if isinstance(response, dict) and response.get('success') is False:
                reason = response.get('error') or 'Browser command failed'
                raise RuntimeError(f'Cannot read live notebook content: {reason}. '
                                   'Check the JupyterLab browser command bridge; '
                                   'no notebook content was returned.')
            payload = response.get('result', response) if isinstance(response, dict) else response
            if not isinstance(payload, dict) or not isinstance(payload.get('content'), dict):
                raise RuntimeError('Cannot read live notebook content: the browser returned '
                                   'an invalid response without notebook content.')
        return response

    run_lab_command._flinc_content_guard = True
    notebook.run_lab_command = run_lab_command
