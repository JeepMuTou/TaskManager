import os
import sys
import json
import threading
import urllib.request
import zipfile
import subprocess
from pathlib import Path

class EnvManager:
    def __init__(self, tasks_dir: str):
        self.tasks_dir = Path(tasks_dir)
        
        if getattr(sys, 'frozen', False):
            self.root_dir = Path(sys.executable).parent
        else:
            self.root_dir = Path(__file__).parent.parent.parent
            
        self.python_env_dir = self.root_dir / "python_env"
        
    def get_required_libs(self):
        import ast
        
        libs = set(["pyside6", "schedule"]) # Baseline libs used by our tools
        if not self.tasks_dir.exists():
            return list(libs)
            
        # Common standard library modules to ignore
        stdlib = {
            'abc', 'argparse', 'ast', 'asyncio', 'base64', 'collections', 'concurrent',
            'contextlib', 'copy', 'csv', 'dataclasses', 'datetime', 'decimal', 'enum',
            'functools', 'hashlib', 'html', 'http', 'importlib', 'inspect', 'io',
            'itertools', 'json', 'logging', 'math', 'multiprocessing', 'os', 'pathlib',
            'pickle', 'platform', 'queue', 'random', 're', 'shutil', 'socket', 'sqlite3',
            'ssl', 'string', 'struct', 'subprocess', 'sys', 'tempfile', 'threading',
            'time', 'traceback', 'typing', 'urllib', 'uuid', 'warnings', 'xml', 'zipfile',
            'tkinter', 'venv', 'glob', 'stat', 'builtins', 'calendar', 'math', 'maths',
            'difflib', 'getpass', 'configparser', 'ctypes', 'email', 'urllib3'
        }
        
        if hasattr(sys, 'stdlib_module_names'):
            stdlib.update(sys.stdlib_module_names)
        if hasattr(sys, 'builtin_module_names'):
            stdlib.update(sys.builtin_module_names)
        
        # Mapping from import name to pip package name
        mappings = {
            'cv2': 'opencv-python',
            'bs4': 'beautifulsoup4',
            'win32com': 'pywin32',
            'win32api': 'pywin32',
            'win32gui': 'pywin32',
            'win32con': 'pywin32',
            'win32ui': 'pywin32',
            'win32clipboard': 'pywin32',
            'pythoncom': 'pywin32',
            'PIL': 'Pillow',
            'sklearn': 'scikit-learn',
            'yaml': 'pyyaml',
            'dotenv': 'python-dotenv',
            'dateutil': 'python-dateutil',
            'pyside6': 'PySide6'
        }
            
        for item in self.tasks_dir.iterdir():
            if item.is_dir():
                # 1. Check requirements.txt
                req_file = item / "requirements.txt"
                if req_file.exists():
                    try:
                        with open(req_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    import re
                                    name = re.split(r'[=><!~]', line)[0].strip()
                                    if name:
                                        libs.add(name.lower())
                    except:
                        pass
                
                # 2. Parse all .py scripts for imports
                for py_file in item.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            tree = ast.parse(f.read(), filename=str(py_file))
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    root_mod = alias.name.split('.')[0]
                                    if root_mod not in stdlib:
                                        pkg_name = mappings.get(root_mod, root_mod)
                                        libs.add(pkg_name.lower())
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    root_mod = node.module.split('.')[0]
                                    if root_mod not in stdlib:
                                        pkg_name = mappings.get(root_mod, root_mod)
                                        libs.add(pkg_name.lower())
                    except Exception as e:
                        print(f"Failed to parse {py_file}: {e}")
                        
        return list(libs)
        
    def get_current_python(self):
        possible_envs = [
            self.root_dir / "python_env" / "python.exe",
            self.root_dir / "env" / "Scripts" / "python.exe",
            self.root_dir / ".venv" / "Scripts" / "python.exe"
        ]
        for env_exe in possible_envs:
            if env_exe.exists():
                return str(env_exe)
                
        if getattr(sys, 'frozen', False):
            return "python"
        return sys.executable

    def check_env(self):
        py_exe = self.get_current_python()
        
        has_python = False
        try:
            subprocess.run([py_exe, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            has_python = True
        except:
            has_python = False
            
        req_libs = self.get_required_libs()
        missing_libs = []
        
        if has_python:
            try:
                output = subprocess.check_output([py_exe, "-m", "pip", "freeze"], text=True)
                installed_pkgs = []
                for line in output.lower().split('\n'):
                    if '==' in line:
                        installed_pkgs.append(line.split('==')[0].strip())
                    elif '@' in line:
                        installed_pkgs.append(line.split('@')[0].strip())
                        
                for lib in req_libs:
                    if lib.lower() not in installed_pkgs:
                        missing_libs.append(lib)
            except:
                missing_libs = req_libs
        else:
            missing_libs = req_libs
            
        is_ok = has_python and (len(missing_libs) == 0)
        return is_ok, not has_python, missing_libs
        
    def start_auto_fix(self):
        threading.Thread(target=self._auto_fix_worker, daemon=True).start()
        
    def _auto_fix_worker(self):
        try:
            self.python_env_dir.mkdir(parents=True, exist_ok=True)
            py_exe = self.python_env_dir / "python.exe"
            
            if not py_exe.exists():
                print("Downloading Python Embeddable...")
                zip_url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"
                zip_path = self.python_env_dir / "python.zip"
                urllib.request.urlretrieve(zip_url, zip_path)
                
                print("Extracting Python...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.python_env_dir)
                    
                zip_path.unlink()
                
                pth_file = self.python_env_dir / "python310._pth"
                if pth_file.exists():
                    content = pth_file.read_text(encoding='utf-8')
                    content = content.replace("#import site", "import site")
                    pth_file.write_text(content, encoding='utf-8')
                    
                print("Downloading get-pip.py...")
                get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
                get_pip_path = self.python_env_dir / "get-pip.py"
                urllib.request.urlretrieve(get_pip_url, get_pip_path)
                
                print("Installing pip...")
                subprocess.run([str(py_exe), str(get_pip_path)], check=True)
                
            reqs = self.get_required_libs()
            if reqs:
                print("Installing requirements:", reqs)
                subprocess.run([str(py_exe), "-m", "pip", "install"] + reqs, check=True)
                
            print("Auto fix complete!")
        except Exception as e:
            print(f"Auto fix failed: {e}")
