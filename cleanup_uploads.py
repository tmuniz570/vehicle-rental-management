import os
import sys
import glob
import json
import urllib.parse
from app import app
from database import Client, Contract, Inspection, ContractAttachment

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
DEMO_ASSETS_FOLDER = os.path.join(BASE_DIR, 'static', 'demo_assets')
EXCLUDE_PREFIXES = ('demo_', 'placeholder')
EXCLUDE_FILES = {'.gitkeep', '.gitignore'}

def extract_clean_filename(val):
    """Extracts and cleans a relative/absolute URL or filename from a database field."""
    if not val or not isinstance(val, str):
        return None
    cleaned = val.strip().strip('"\'[]')
    if not cleaned:
        return None
    # Remove query string / cache busters (e.g. ?v=1)
    cleaned = cleaned.split('?')[0].strip()
    # Decode URL-encoded characters (e.g. %20 -> space)
    cleaned = urllib.parse.unquote(cleaned)
    # Extract basename
    name = os.path.basename(cleaned)
    return name if name else None

def collect_valid_files():
    """Scans all database models and returns a set of valid filenames referenced in DB."""
    valid_files = set()

    # 1. Clients
    for c in Client.query.all():
        for field in [c.url_habilitacao, c.url_habilitacao_verso, c.url_cbt, c.url_comprovante_endereco]:
            fname = extract_clean_filename(field)
            if fname:
                valid_files.add(fname)

    # 2. Contracts (live attachments & immutable snapshots)
    for c in Contract.query.all():
        for field in [
            c.url_seguro, c.url_comprovante_deposito,
            c.assinatura_cliente_inicial, c.assinatura_cliente_devolucao,
            c.url_habilitacao, c.url_habilitacao_verso, c.url_cbt, c.url_comprovante_endereco
        ]:
            fname = extract_clean_filename(field)
            if fname:
                valid_files.add(fname)

    # 3. Contract Attachments
    for a in ContractAttachment.query.all():
        fname = extract_clean_filename(a.url_arquivo)
        if fname:
            valid_files.add(fname)

    # 4. Inspections (can be comma-separated or JSON list)
    for i in Inspection.query.all():
        if not i.url_fotos:
            continue
        raw = i.url_fotos.strip()
        # Try JSON parsing first
        if (raw.startswith('[') and raw.endswith(']')) or (raw.startswith('{') and raw.endswith('}')):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    for item in parsed:
                        fname = extract_clean_filename(str(item))
                        if fname:
                            valid_files.add(fname)
                    continue
            except Exception:
                pass
        
        # Fallback to comma-separated list
        urls = [u.strip() for u in raw.split(',') if u.strip()]
        for u in urls:
            fname = extract_clean_filename(u)
            if fname:
                valid_files.add(fname)

    return valid_files

def run_cleanup(dry_run=False, verbose=False):
    mode_str = "[DRY-RUN MODE - NO FILES WILL BE DELETED]" if dry_run else "[ACTIVE DELETION MODE]"
    print(f"\n=== Starting Uploads Cleanup {mode_str} ===")
    print(f"Directory: {UPLOAD_FOLDER}")

    if not os.path.exists(UPLOAD_FOLDER):
        print(f"Uploads folder '{UPLOAD_FOLDER}' does not exist. Nothing to clean.")
        return

    # Collect demo asset names from static/demo_assets to ensure they are never deleted
    protected_demo_assets = set()
    if os.path.exists(DEMO_ASSETS_FOLDER):
        protected_demo_assets = set(os.listdir(DEMO_ASSETS_FOLDER))

    with app.app_context():
        valid_files = collect_valid_files()

    print(f"-> Found {len(valid_files)} valid file reference(s) in the database.")
    if verbose:
        for vf in sorted(valid_files):
            print(f"   [DB Valid] {vf}")

    all_disk_entries = glob.glob(os.path.join(UPLOAD_FOLDER, '*'))
    deleted_count = 0
    protected_count = 0
    valid_count = 0
    total_bytes_saved = 0

    orphans = []

    for filepath in all_disk_entries:
        if not os.path.isfile(filepath):
            continue

        filename = os.path.basename(filepath)

        # Skip system / hidden files (.gitkeep, etc.)
        if filename.startswith('.') or filename in EXCLUDE_FILES:
            protected_count += 1
            continue

        # Skip demo asset prefixes or files matching static/demo_assets folder
        if filename.startswith(EXCLUDE_PREFIXES) or filename in protected_demo_assets:
            protected_count += 1
            continue

        # Check if file is referenced in database
        if filename in valid_files:
            valid_count += 1
            continue

        # Orphan file identified
        file_size = os.path.getsize(filepath)
        orphans.append((filepath, filename, file_size))

    print(f"-> Scanned {len(all_disk_entries)} file(s) on disk.")
    print(f"   - Valid & referenced: {valid_count}")
    print(f"   - Protected demo/system files: {protected_count}")
    print(f"   - Orphan file(s) found: {len(orphans)}")

    for filepath, filename, file_size in orphans:
        total_bytes_saved += file_size
        if dry_run:
            print(f"   [WOULD DELETE] {filename} ({file_size / 1024:.1f} KB)")
        else:
            try:
                os.remove(filepath)
                deleted_count += 1
                print(f"   [DELETED] {filename} ({file_size / 1024:.1f} KB)")
            except Exception as e:
                print(f"   [ERROR] Failed to delete {filename}: {e}")

    mb_saved = total_bytes_saved / 1024 / 1024
    print("\n=======================================================")
    if dry_run:
        print(f"✓ Dry-run completed! {len(orphans)} orphan file(s) would be deleted.")
        print(f"✓ Potential disk space to free: {mb_saved:.2f} MB ({total_bytes_saved:,} bytes)")
        print("Run without --dry-run to permanently delete orphan files.")
    else:
        print(f"✓ Cleanup finished! Successfully deleted {deleted_count} orphan file(s).")
        print(f"✓ Total disk space freed: {mb_saved:.2f} MB ({total_bytes_saved:,} bytes)")
    print("=======================================================\n")

if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    run_cleanup(dry_run=dry_run, verbose=verbose)
