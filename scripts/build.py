import shutil
import subprocess
import os
import sys

# Obtener la ruta al directorio raíz del proyecto
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
print(f"root_dir: {root_dir}")

# Directorios a eliminar
dirs_to_remove = [os.path.join(root_dir, 'build'), os.path.join(root_dir, 'dist')]

# Borrar los directorios si existen
for dir in dirs_to_remove:
    if os.path.exists(dir):
        shutil.rmtree(dir)
        print(f"Deleted directory {dir}")

# Cambiar el directorio de trabajo al directorio raíz del proyecto
os.chdir(root_dir)
setup_path = os.path.join(root_dir, 'setup.py')
# Comprobar si el entorno virtual está activado
if sys.prefix == sys.base_prefix:
    print("El entorno virtual no está activado.")
else:
    print("Entorno virtual activado.")

# Ejecutar setup.py para generar el wheel y sdist

print(f"setup_path: {setup_path}")
subprocess.run([sys.executable, setup_path, "sdist", "bdist_wheel"])
