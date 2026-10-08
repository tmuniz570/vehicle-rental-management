"""
diagnose_v5c.py - Diagnostic and Self-Healing Tool for Motorcycle V5C Documents
FF Motors APP

Usage:
  python diagnose_v5c.py           # Dry-run analysis (safe, read-only)
  python diagnose_v5c.py --fix     # Repairs duplicate shared file references by cloning files
"""

import os
import sys
import shutil
import argparse
from app import app
from database import db, MotorcycleV5C

def run_diagnostic(apply_fix=False):
    print("=" * 70)
    print("🔍 FF MOTORS - V5C DOCUMENT DIAGNOSTIC & INTEGRITY AUDITOR")
    print("=" * 70)
    
    with app.app_context():
        upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static', 'uploads'))
        records = MotorcycleV5C.query.order_by(MotorcycleV5C.id.asc()).all()
        
        print(f"📁 Upload Folder: {upload_folder}")
        print(f"📊 Total V5C records in database: {len(records)}\n")
        
        url_map = {}
        missing_files = []
        
        for r in records:
            url = r.url_arquivo or ''
            fname = os.path.basename(url) if url else ''
            fpath = os.path.join(upload_folder, fname) if fname else ''
            
            exists = os.path.exists(fpath) if fpath else False
            if not exists:
                missing_files.append((r, fpath))
                
            if url:
                url_map.setdefault(url, []).append((r, fpath, exists))
                
        # 1. Duplicates Report
        duplicates = {url: recs for url, recs in url_map.items() if len(recs) > 1}
        print(f"🔁 Duplicate Shared File URLs: {len(duplicates)}")
        
        repaired_count = 0
        
        for url, group in duplicates.items():
            print(f"\n⚠️ URL shared by {len(group)} records: {url}")
            primeiro = group[0]
            print(f"   - Record #{primeiro[0].id} (Plate: {primeiro[0].placa}, Category: {primeiro[0].categoria_doc}, Exists on disk: {primeiro[2]}) [KEEP ORIGINAL]")
            
            for dup_rec, fpath, exists in group[1:]:
                print(f"   - Record #{dup_rec.id} (Plate: {dup_rec.placa}, Category: {dup_rec.categoria_doc}, Exists on disk: {exists}) [SHARED DUPLICATE]")
                
                if apply_fix and exists:
                    base_name, ext = os.path.splitext(os.path.basename(dup_rec.url_arquivo))
                    new_filename = f"{base_name}_split_{dup_rec.id}{ext}"
                    new_fpath = os.path.join(upload_folder, new_filename)
                    
                    try:
                        shutil.copyfile(fpath, new_fpath)
                        dup_rec.url_arquivo = f"/static/uploads/{new_filename}"
                        repaired_count += 1
                        print(f"     ✅ CLONED to {new_filename} and updated Record #{dup_rec.id}")
                    except Exception as e:
                        print(f"     ❌ Failed to clone file: {e}")
                        
        if apply_fix and repaired_count > 0:
            db.session.commit()
            print(f"\n🎉 Successfully decoupled {repaired_count} shared file references into independent physical files!")
            
        # 2. Missing Files Report
        print(f"\n❌ Missing Physical Files (404 on disk): {len(missing_files)}")
        for r, fpath in missing_files:
            print(f"   - Record #{r.id} | Plate: {r.placa} | Name: {r.nome_original} | Path missing: {os.path.basename(fpath)}")
            
        print("\n" + "=" * 70)
        if len(duplicates) == 0 and len(missing_files) == 0:
            print("✅ 100% HEALTHY: All V5C records have unique, valid physical files.")
        else:
            if not apply_fix and len(duplicates) > 0:
                print("💡 TIP: Run 'python diagnose_v5c.py --fix' to decouple shared duplicate files.")
        print("=" * 70)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Diagnose and repair V5C duplicate files")
    parser.add_argument('--fix', action='store_true', help="Decouple duplicate file references by cloning physical files")
    args = parser.parse_args()
    run_diagnostic(apply_fix=args.fix)
