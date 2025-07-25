import jupyter_client
from queue import Empty

def execute_code_in_kernel(code: str) -> list:
    """
    Executes a string of Python code in a temporary Jupyter kernel
    and captures the output.
    """
    # Start a new kernel
    km = jupyter_client.KernelManager()
    km.start_kernel()
    kc = km.client()
    kc.start_channels()

    # Wait for the client to be ready
    try:
        kc.wait_for_ready(timeout=60)
    except RuntimeError:
        kc.stop_channels()
        km.shutdown_kernel()
        raise

    # Execute the code
    kc.execute(code)
    results = []

    while True:
        try:
            # Get messages from the kernel, with a timeout
            msg = kc.get_iopub_msg(timeout=10)
        except Empty:
            # No more messages, break the loop
            break

        # Check the message type and content
        msg_type = msg['header']['msg_type']
        
        if msg.get('parent_header', {}).get('msg_type') != 'execute_request':
             continue # only process messages from our execution

        if msg_type == 'status' and msg['content']['execution_state'] == 'idle':
            # Kernel is done executing, break the loop
            break
        elif msg_type == 'stream':
            # This is a print() statement or other stdout
            results.append({'type': 'stdout', 'text': msg['content']['text']})
        elif msg_type == 'execute_result':
            # This is the result of the last line of a cell
            data = msg['content']['data'].get('text/plain', '')
            results.append({'type': 'result', 'text': data})
        elif msg_type == 'error':
            # An error occurred
            error_content = {
                'type': 'error',
                'ename': msg['content']['ename'],
                'evalue': msg['content']['evalue'],
                'traceback': msg['content']['traceback'],
            }
            results.append(error_content)
            break

    # Shut down the kernel and clean up
    kc.stop_channels()
    km.shutdown_kernel(now=True)
    return results
