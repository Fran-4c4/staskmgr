import shutil
import subprocess
import os
import sys

# Obtener la ruta al directorio raíz del proyecto
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
print(f"root_dir: {root_dir}")
# Cambiar el directorio de trabajo al directorio raíz del proyecto
os.chdir(root_dir)

def get_version():
    # Obtener la versión del archivo __ini__.py
    ini_path = os.path.join(root_dir, "tmgr",'__ini__.py') 
    result = subprocess.run([sys.executable, 'setup.py', '--version'], capture_output=True, text=True)
    return result.stdout.strip()

def commit_and_tag(version):
    # Hacer commit y crear el tag de Git
    # subprocess.run(['git', 'add', '.'])
    # subprocess.run(['git', 'commit', '-m', f"Versión {version}"])
    subprocess.run(['git', 'tag', '-a', f"v{version}", '-m', f"Release {version}"])
    subprocess.run(['git', 'push', 'origin', 'main', '--tags'])


if __name__ == '__main__':
    version = get_version()
    commit_and_tag(version)
    # upload_to_pypi()
