import jupyter_client
from queue import Empty
import json

def execute_code_in_kernel(code: str) -> list:
    """
    Executes a string of Python code in a temporary Jupyter kernel
    and captures the output, correctly handling JSON.
    """
    km = jupyter_client.KernelManager()
    km.start_kernel()
    kc = km.client()
    kc.start_channels()

    try:
        kc.wait_for_ready(timeout=60)
    except RuntimeError:
        kc.stop_channels()
        km.shutdown_kernel()
        raise

    kc.execute(code)
    results = []

    while True:
        try:
            msg = kc.get_iopub_msg(timeout=20)
        except Empty:
            break

        msg_type = msg['header']['msg_type']
        content = msg.get('content', {})

        if msg_type == 'status' and content.get('execution_state') == 'idle':
            break
        elif msg_type == 'stream':
            results.append({'type': 'stdout', 'text': content.get('text', '')})
        elif msg_type == 'execute_result':
            # --- THIS IS THE FIX ---
            # Check for rich JSON output first, which is what fig.to_json() produces.
            if 'application/json' in content.get('data', {}):
                # We dump and reload to ensure it's a clean, double-quoted JSON string
                json_data = json.dumps(content['data']['application/json'])
                results.append({'type': 'json_result', 'text': json_data})
            # Fallback to plain text if no JSON is available
            else:
                text_data = content.get('data', {}).get('text/plain', '')
                results.append({'type': 'result', 'text': text_data})
        elif msg_type == 'error':
            results.append({
                'type': 'error',
                'ename': content.get('ename', 'Unknown error'),
                'evalue': content.get('evalue', '...'),
                'traceback': content.get('traceback', []),
            })
            break

    kc.stop_channels()
    km.shutdown_kernel(now=True)
    return results