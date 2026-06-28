import shutil
import subprocess
import os
import sys
import argparse
import importlib.util
from pathlib import Path

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
    print("Tag project")




# Comprobar si el entorno virtual está activado
if sys.prefix == sys.base_prefix:
    print("El entorno virtual no está activado.")
else:
    print("Entorno virtual activado.")
    
def delete_old():
    # Directorios a eliminar
    dirs_to_remove = [os.path.join(root_dir, 'build'), os.path.join(root_dir, 'dist')]

    # Borrar los directorios si existen
    for dir in dirs_to_remove:
        if os.path.exists(dir):
            shutil.rmtree(dir)
            print(f"Deleted directory {dir}")

def build():
    # Ejecutar setup.py para generar el wheel y sdist
    setup_path = os.path.join(root_dir, 'setup.py')   

    print(f"setup_path: {setup_path}")
    subprocess.run([sys.executable, setup_path, "sdist", "bdist_wheel"], check=True)
    print("Package build")


def get_dist_files():
    """Return built distribution artifacts ready for twine upload."""

    dist_dir = Path(root_dir) / "dist"
    dist_files = sorted(
        path for path in dist_dir.iterdir()
        if path.is_file() and path.suffix in {".whl", ".gz", ".zip"}
    )
    if not dist_files:
        raise RuntimeError("No distribution files found in dist/. Build the package first.")
    return [str(path) for path in dist_files]


def upload_to_pypi():
    if importlib.util.find_spec("twine") is None:
        raise RuntimeError(
            "twine is not installed. Run: "
            f"{sys.executable} -m pip install -r requirements-dev.txt"
        )
    dist_files = get_dist_files()
    try:
        subprocess.run(
            [sys.executable, "-m", "twine", "upload", *dist_files, "--verbose"],
            check=True,
        )
    except subprocess.CalledProcessError as ex:
        if ex.returncode == 1:
            print("Upload failed. Check PyPI credentials, package version, and twine output above.")
        raise
    print("Package uploaded")

def ask():
    print("\n")
    version = get_version()
    print(f"Options for version {version}:")
    print("1. build package")
    print("2. upload to pypi")
    print("3. Tag package using package version")
    print("4. Full: build, upload, tag")  
    print("0. Exit")    
    opcion = input("Select an option: ")

    return opcion

if __name__ == '__main__':
    
    # parser = argparse.ArgumentParser(description='Task operations')
    # parser.add_argument('--full', help='Execute all actions')
    # parser.add_argument('--build', help='Build package')
    # parser.add_argument('--tag', help='Tag version using package version')
    # args = parser.parse_args()
    
    
    opcion=-1
    while opcion!='0':        
        opcion=ask()
        version = get_version()
        if opcion=='1':          
            delete_old()
            build()                
        elif opcion=='2':     
            upload_to_pypi()     
        elif opcion=='3':     
            commit_and_tag(version)
        elif opcion=='4':        
            delete_old()
            build()                
            upload_to_pypi()
            commit_and_tag(version)                
          
