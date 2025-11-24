import argparse
import sys
import os
import shutil
from .manager import ArchiveManager
from nercone_modern.logging import ModernLogging
from nercone_modern.color import ModernColor

logger = ModernLogging("nyarchiver", show_level=False, show_proc=False)

def interactive_mode():
    logger.log("Entering Interactive Mode. Type 'help' for commands.", "INFO")

    current_archive = None
    mgr = ArchiveManager()

    try:
        while True:
            name_display = os.path.basename(current_archive) if current_archive else "New/Unsaved"
            status_color = 'cyan' if current_archive else 'yellow'
            prompt_str = f"[{ModernColor.color(status_color)}{name_display}{ModernColor.RESET}] >"

            cmd_input = logger.prompt(prompt_str, show_choices=False)
            
            if not cmd_input:
                continue

            parts = cmd_input.strip().split()
            if not parts: continue
            cmd = parts[0].lower()
            args = parts[1:]

            try:
                if cmd in ["exit", "quit", "q"]:
                    break

                elif cmd == "help":
                    print(f"""
{ModernColor.color('blue')}Commands:{ModernColor.RESET}
  {ModernColor.color('green')}File Operations:{ModernColor.RESET}
    open <path> [pwd]      Import an archive
    save <path> [fmt]      Export/Save current state (fmt: zip, tar, 7z...)
    new / close            Close current archive and start fresh
    info                   Show details about current session

  {ModernColor.color('green')}Content Operations:{ModernColor.RESET}
    ls                     List files in current working state
    add <src> [dest_path]  Add a local file/dir to the archive
    rm <path_in_arc>       Remove a file/dir from the archive

  {ModernColor.color('green')}Security:{ModernColor.RESET}
    enc <pass>             Set encryption password for saving
    dec <pass>             Retry import with password (if failed previously)
    
  exit                   Exit
                    """)

                elif cmd == "open":
                    if not args:
                        logger.log("Usage: open <path> [password]", "WARN")
                        continue
                    path = args[0].strip().replace("'", "").replace("\"", "")
                    pwd = args[1] if len(args) > 1 else None

                    mgr.close()
                    mgr = ArchiveManager()

                    try:
                        mgr.import_archive(path, password=pwd)
                        current_archive = path
                    except Exception:
                        current_archive = f"{path} (Load Failed)"

                elif cmd == "save":
                    save_path = None
                    fmt = None

                    if not args:
                        if current_archive and "Failed" not in current_archive:
                            save_path = logger.prompt("Output path", default=current_archive)
                        else:
                            save_path = logger.prompt("Output path")
                    else:
                        save_path = args[0]
                        if len(args) > 1:
                            fmt = args[1]

                    if save_path:
                        mgr.export(save_path, compression_format=fmt)
                        current_archive = save_path

                elif cmd in ["new", "close"]:
                    mgr.close()
                    mgr = ArchiveManager()
                    current_archive = None
                    logger.log("Workspace cleared. Ready for new archive.")

                elif cmd == "info":
                    logger.log(f"Current Archive: {current_archive}")
                    logger.log(f"Temp Directory : {mgr.temp_dir}")
                    enc_status = "Enabled" if mgr._password_for_export else "Disabled"
                    logger.log(f"Encryption     : {enc_status}")

                    files = mgr.list_files()
                    logger.log(f"Total Files    : {len(files)}")

                elif cmd == "ls":
                    files = mgr.list_files()
                    if not files:
                        logger.log(" (Empty) ")
                    for f in files:
                        logger.log(f" {f}")

                elif cmd == "add":
                    if not args:
                        logger.log("Usage: add <local_path> [dest_path_in_archive]", "WARN")
                        continue
                    src = args[0]
                    dst = args[1] if len(args) > 1 else ""
                    mgr.add(src, dest_path_in_archive=dst)

                elif cmd == "rm":
                    if not args:
                        logger.log("Usage: rm <path_in_archive>", "WARN")
                        continue
                    mgr.remove(args[0])

                elif cmd == "enc":
                    if not args:
                        pwd = logger.prompt("Enter Password to Set")
                    else:
                        pwd = args[0]
                    if pwd:
                        mgr.encrypt(pwd)

                elif cmd == "dec":
                    if not args:
                        pwd = logger.prompt("Enter Password to Decrypt")
                    else:
                        pwd = args[0]
                    if pwd:
                        mgr.decrypt(pwd)

                else:
                    logger.log(f"Unknown command: {cmd}", "WARN")

            except Exception as e:
                logger.log(f"Error: {e}", "ERROR")

    except KeyboardInterrupt:
        print()
        logger.log("Interrupted. Exiting...", "WARN")
    finally:
        mgr.close()

def main():
    parser = argparse.ArgumentParser(prog="nyarchiver", description="Nercone Archiver")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    def add_auth_args(p):
        p.add_argument("--password", "-p", help="Password for encrypted archives", default=None)

    def add_output_args(p):
        p.add_argument("--out", "-o", help="Output archive path (default: overwrite original if modifying)", default=None)
        p.add_argument("--format", "-f", help="Force compression format (zip, tar, 7z, etc.)", default=None)

    # LS: List files
    parser_ls = subparsers.add_parser("ls", help="List files in an archive")
    parser_ls.add_argument("archive", help="Path to archive file")
    add_auth_args(parser_ls)

    # CREATE: Create new archive
    parser_create = subparsers.add_parser("create", help="Create a new archive")
    parser_create.add_argument("archive", help="Destination archive path")
    parser_create.add_argument("source", help="Source file or directory to add")
    parser_create.add_argument("--dest-path", "-d", help="Path inside the archive", default="")
    add_auth_args(parser_create)
    parser_create.add_argument("--format", "-f", help="Force compression format", default=None)

    # EXTRACT: Extract archive
    parser_extract = subparsers.add_parser("extract", help="Extract an archive")
    parser_extract.add_argument("archive", help="Path to archive file")
    parser_extract.add_argument("dest", nargs="?", help="Destination directory (default: current dir)", default=".")
    add_auth_args(parser_extract)

    # ADD: Add file to EXISTING archive
    parser_add = subparsers.add_parser("add", help="Add file/dir to an existing archive")
    parser_add.add_argument("archive", help="Path to existing archive")
    parser_add.add_argument("source", help="Source file or directory to add")
    parser_add.add_argument("--dest-path", "-d", help="Path inside the archive", default="")
    add_auth_args(parser_add)
    add_output_args(parser_add)

    # RM: Remove file from EXISTING archive
    parser_rm = subparsers.add_parser("rm", help="Remove file/dir from an existing archive")
    parser_rm.add_argument("archive", help="Path to existing archive")
    parser_rm.add_argument("target", help="Path inside the archive to remove")
    add_auth_args(parser_rm)
    add_output_args(parser_rm)

    args = parser.parse_args()

    if not args.command:
        return interactive_mode()

    mgr = ArchiveManager()
    try:
        # --- LS ---
        if args.command == "ls":
            mgr.import_archive(args.archive, password=args.password)
            files = mgr.list_files()
            logger.log(f"{ModernColor.color('green')}Files in {args.archive}:{ModernColor.RESET}")
            if not files:
                logger.log(" (Empty) ")
            for f in files:
                logger.log(f" - {f}")

        # --- CREATE ---
        elif args.command == "create":
            mgr.add(args.source, dest_path_in_archive=args.dest_path)
            if args.password:
                mgr.encrypt(args.password)
            mgr.export(args.archive, compression_format=args.format)

        # --- EXTRACT ---
        elif args.command == "extract":
            mgr.import_archive(args.archive, password=args.password)
            dest_path = os.path.abspath(args.dest)
            os.makedirs(dest_path, exist_ok=True)

            logger.log(f"Extracting to {dest_path}...")
            shutil.copytree(mgr.temp_dir, dest_path, dirs_exist_ok=True)
            logger.log("Extraction finished.")

        # --- ADD (Update) ---
        elif args.command == "add":
            mgr.import_archive(args.archive, password=args.password)
            mgr.add(args.source, dest_path_in_archive=args.dest_path)
            if args.password:
                mgr.encrypt(args.password)
            output_path = args.out if args.out else args.archive
            mgr.export(output_path, compression_format=args.format)

        # --- RM (Remove) ---
        elif args.command == "rm":
            mgr.import_archive(args.archive, password=args.password)
            mgr.remove(args.target)
            if args.password:
                mgr.encrypt(args.password)
            output_path = args.out if args.out else args.archive
            mgr.export(output_path, compression_format=args.format)

    except Exception as e:
        logger.log(str(e), "ERROR")
        sys.exit(1)
    finally:
        mgr.close()

if __name__ == "__main__":
    main()
