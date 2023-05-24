import subprocess

def postprocess_file(f):
    return subprocess.run(['scripts/postprocess.sh', f], capture_output=True).stdout.decode()