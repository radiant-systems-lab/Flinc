"""Give patched prebuilt assets new URLs so immutable browser caches refresh."""
import hashlib
import json
from pathlib import Path


def rebuild_asset_names(extension_dir):
    root=Path(extension_dir)
    metadata=json.loads((root/'package.json').read_text())
    entry=root/metadata['jupyterlab']['_build']['load']
    original_entry=entry.read_text()
    import re
    match=re.search(r'509:"([0-9a-f]+)"',original_entry)
    if not match:
        raise ValueError('Unsupported commands-toolkit build: chunk 509 not found')
    old_hash=match.group(1)
    chunk=root/'static'/f'509.{old_hash}.js'
    new_hash=hashlib.sha256(chunk.read_bytes()).hexdigest()[:20]
    new_chunk=chunk.with_name(f'509.{new_hash}.js')
    new_chunk.write_bytes(chunk.read_bytes())
    updated_entry=original_entry.replace(old_hash,new_hash)
    entry_hash=hashlib.sha256(updated_entry.encode()).hexdigest()[:20]
    new_entry=entry.with_name(f'remoteEntry.{entry_hash}.js')
    new_entry.write_text(updated_entry)
    metadata['jupyterlab']['_build']['load']='static/'+new_entry.name
    (root/'package.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return new_chunk.name,new_entry.name


if __name__=='__main__':
    import sys
    print(rebuild_asset_names(sys.argv[1]))
