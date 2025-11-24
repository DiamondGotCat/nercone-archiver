import os
import shutil
import tempfile
from pathlib import Path
import zipfile
import tarfile
from nercone_modern.logging import ModernLogging
from nercone_modern.progressbar import ModernProgressBar

try:
    import py7zr
except ImportError:
    py7zr = None

try:
    import rarfile
except ImportError:
    rarfile = None

try:
    import pyzipper
    PYZIPPER_AVAILABLE = True
except ImportError:
    PYZIPPER_AVAILABLE = False

logger = ModernLogging("archivemanager", show_proc=False, show_level=False)

class ArchiveManager:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self._password_for_export = None
        self._imported_archive_path = None
        self._is_encrypted_import = False
        logger.log(f"ArchiveManager initialized. Temp directory: {self.temp_dir}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        shutil.rmtree(self.temp_dir)
        logger.log(f"Temporary directory {self.temp_dir} removed.")

    def _get_format(self, path):
        name = os.path.basename(path).lower()
        if name.endswith('.tar.gz'): return 'tar.gz'
        if name.endswith('.tar.xz'): return 'tar.xz'
        if name.endswith('.tgz'): return 'tar.gz'
        return Path(path).suffix[1:].lower()

    def import_archive(self, archive_path, password=None):
        if not Path(archive_path).exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        self._imported_archive_path = archive_path
        fmt = self._get_format(archive_path)
        logger.log(f"Importing '{archive_path}' (format: {fmt})")

        try:
            if fmt == 'zip':
                self._import_zip_with_progress(archive_path, password)
            elif fmt in ['tar', 'tar.gz', 'gz', 'tar.xz', 'xz']:
                self._import_tar_with_progress(archive_path, fmt)
            elif fmt == '7z':
                if not py7zr: raise ImportError("py7zr is not installed.")
                with py7zr.SevenZipFile(archive_path, 'r', password=password) as szf:
                    files = szf.getnames()
                    total_files = len(files)
                    bar = ModernProgressBar(total_files, "Import 7z")

                    for fname in files:
                        szf.extract(targets=[fname], path=self.temp_dir)
                        bar.update(1)
                    bar.finish()
            elif fmt == 'rar':
                if not rarfile: raise ImportError("rarfile is not installed.")
                with rarfile.RarFile(archive_path, 'r', pwd=password) as rf:
                    members = rf.infolist()
                    total_files = len(members)
                    bar = ModernProgressBar(total_files, "Import Rar")
                    
                    for member in members:
                        rf.extract(member, self.temp_dir)
                        bar.update(1)
                    bar.finish()
            else:
                raise ValueError(f"Unsupported import format: {fmt}")

            logger.log("Import successful.")

        except Exception as e:
            if "password" in str(e).lower() or "encrypted" in str(e).lower() or isinstance(e, RuntimeError):
                self._is_encrypted_import = True
                logger.log(f"Import failed (likely encryption): {e}", "WARN")
            else:
                logger.log(f"Failed to import archive: {e}", "ERROR")
            raise

    def _import_zip_with_progress(self, archive_path, password):
        opener = zipfile.ZipFile
        if PYZIPPER_AVAILABLE:
            try:
                with pyzipper.AESZipFile(archive_path) as zf:
                    if zf.encryption == pyzipper.WZ_AES:
                        opener = pyzipper.AESZipFile
            except:
                pass

        with opener(archive_path, 'r') as zf:
            if password:
                zf.setpassword(password.encode())

            members = zf.infolist()
            total = len(members)
            bar = ModernProgressBar(total, "Import Zip")

            for member in members:
                try:
                    zf.extract(member, self.temp_dir)
                    bar.update(1)
                except RuntimeError as e:
                    bar.finish()
                    if 'password' in str(e).lower():
                        if not password:
                            logger.log("ZIP is encrypted. Use password.", "WARN")
                            self._is_encrypted_import = True
                    raise
            bar.finish()

    def _import_tar_with_progress(self, archive_path, fmt):
        mode = "r:*"
        with tarfile.open(archive_path, mode) as tf:
            members = tf.getmembers()
            total = len(members)
            bar = ModernProgressBar(total, f"Import {fmt.upper()}")

            for member in members:
                tf.extract(member, self.temp_dir)
                bar.update(1)
            bar.finish()

    def export(self, output_path, compression_format=None):
        fmt = compression_format or self._get_format(output_path)
        logger.log(f"Exporting content to '{output_path}' (format: {fmt})")

        file_list = []
        for root, _, files in os.walk(self.temp_dir):
            for file in files:
                file_list.append(os.path.join(root, file))

        total_files = len(file_list)

        if fmt == 'zip':
            self._export_zip_with_progress(output_path, file_list, total_files)
        elif fmt in ['tar', 'tar.gz', 'tar.xz']:
            self._export_tar_with_progress(output_path, fmt, file_list, total_files)
        elif fmt == '7z':
            if not py7zr: raise ImportError("py7zr is not installed.")
            bar = ModernProgressBar(total_files, "Export 7z")
            with py7zr.SevenZipFile(output_path, 'w', password=self._password_for_export) as szf:
                for file_path in file_list:
                    arcname = os.path.relpath(file_path, self.temp_dir)
                    szf.write(file_path, arcname)
                    bar.update(1)
            bar.finish()
        else:
            raise ValueError(f"Unsupported export format: {fmt} or implementation pending.")
            
        logger.log("Export successful.")

    def _export_zip_with_progress(self, output_path, file_list, total_files):
        bar = ModernProgressBar(total_files, "Export Zip")

        compression = zipfile.ZIP_DEFLATED
        encryption = None
        opener = zipfile.ZipFile

        if self._password_for_export and PYZIPPER_AVAILABLE:
            opener = pyzipper.AESZipFile
            encryption = pyzipper.WZ_AES
        elif self._password_for_export:
             logger.log("pyzipper not installed. Creating normal zip.", "WARN")
             pass

        with opener(output_path, 'w', compression=compression, encryption=encryption) as zf:
            if self._password_for_export:
                zf.setpassword(self._password_for_export.encode())
            
            for file_path in file_list:
                arcname = os.path.relpath(file_path, self.temp_dir)
                zf.write(file_path, arcname)
                bar.update(1)
        bar.finish()

    def _export_tar_with_progress(self, output_path, fmt, file_list, total_files):
        mode = "w:gz" if "gz" in fmt else ("w:xz" if "xz" in fmt else "w")
        bar = ModernProgressBar(total_files, f"Export {fmt.upper()}")
        
        with tarfile.open(output_path, mode) as tf:
            for file_path in file_list:
                arcname = os.path.relpath(file_path, self.temp_dir)
                tf.add(file_path, arcname=arcname)
                bar.update(1)
        bar.finish()

    def encrypt(self, password):
        if not isinstance(password, str) or not password:
            raise ValueError("Password must be a non-empty string.")
        self._password_for_export = password
        logger.log("Encryption for export has been enabled.")

    def decrypt(self, password=None):
        if password:
            if not self._imported_archive_path or not self._is_encrypted_import:
                raise RuntimeError("Decrypt with password can only be used after a failed import of an encrypted archive.")
            logger.log(f"Attempting to decrypt '{self._imported_archive_path}' with the new password.")

            for item in os.listdir(self.temp_dir):
                item_path = os.path.join(self.temp_dir, item)
                if os.path.isfile(item_path): os.unlink(item_path)
                elif os.path.isdir(item_path): shutil.rmtree(item_path)

            self.import_archive(self._imported_archive_path, password=password)
            self._is_encrypted_import = False
        else:
            if self._password_for_export:
                self._password_for_export = None
                logger.log("Encryption for export has been disabled.")
            else:
                logger.log("Encryption for export was not enabled.")

    def _resolve_path(self, path_in_archive):
        safe_path = os.path.normpath(path_in_archive).lstrip('/\\')
        full_path = Path(self.temp_dir) / safe_path
        if not str(full_path.resolve()).startswith(str(Path(self.temp_dir).resolve())):
            pass
        return full_path

    def add(self, source_path, dest_path_in_archive=''):
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source_path}")

        if source.is_dir():
            files_to_copy = list(source.rglob('*'))
            bar = ModernProgressBar(len(files_to_copy), "Add Files")
        else:
            bar = None

        dest_path = self._resolve_path(dest_path_in_archive)
        
        if source.is_dir():
            final_dest = dest_path / source.name
            shutil.copytree(source, final_dest)
            if bar: bar.finish()
        else:
            if dest_path.is_dir() or dest_path_in_archive.endswith('/'):
                 final_dest = dest_path
            else:
                 final_dest = dest_path.parent
            final_dest.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, final_dest / source.name if final_dest.is_dir() else final_dest)

        logger.log(f"Added '{source_path}' to archive.")

    def remove(self, path_in_archive):
        target_path = self._resolve_path(path_in_archive)
        if not target_path.exists():
            raise FileNotFoundError(f"Path not found: '{path_in_archive}'")
        
        if target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            target_path.unlink()
        logger.log(f"Removed '{path_in_archive}'.")

    def list_files(self, path_in_archive='.'):
        target_path = self._resolve_path(path_in_archive)
        paths = []
        if target_path.exists():
            for p in target_path.rglob('*'):
                paths.append(str(p.relative_to(self.temp_dir)))
        return sorted(paths)
