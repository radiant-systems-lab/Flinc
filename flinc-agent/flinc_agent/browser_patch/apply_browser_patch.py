"""Apply the compatibility fix to commands-toolkit 0.2.0's prebuilt bundle."""
import json
import re
from pathlib import Path
from .cache_bust import rebuild_asset_names


def patch(extension_dir):
    root=Path(extension_dir)
    metadata=json.loads((root/'package.json').read_text())
    if metadata['version']!='0.2.0':
        raise ValueError('This prebuilt patch targets commands-toolkit 0.2.0; port the source helpers for other versions')
    entry=(root/metadata['jupyterlab']['_build']['load']).read_text()
    match=re.search(r'509:"([0-9a-f]+)"',entry)
    if not match:raise ValueError('Unsupported prebuilt bundle')
    chunk=root/'static'/f'509.{match.group(1)}.js'
    text=chunk.read_text()
    old='const n=crypto.randomUUID()'
    new='const n=(()=>{if(typeof crypto.randomUUID==="function")return crypto.randomUUID();const e=crypto.getRandomValues(new Uint8Array(16));e[6]=e[6]&15|64;e[8]=e[8]&63|128;const t=Array.from(e,e=>e.toString(16).padStart(2,"0")).join("");return`${t.slice(0,8)}-${t.slice(8,12)}-${t.slice(12,16)}-${t.slice(16,20)}-${t.slice(20)}`})()'
    if old in text:text=text.replace(old,new)
    elif new not in text:raise ValueError('Cannot locate web client ID initialization')
    hook='activate:e=>{const{commands:t}=e,o=e.serviceManager.events;'
    helper=Path(__file__).with_name('notebook-commands.js').read_text()
    if '// Called from the existing commands-toolkit' in text:
        start=text.index('// Called from the existing commands-toolkit');end=text.index(';registerFlincNotebookCommands(e)})();',start)
        text=text[:start]+helper+text[end:]
    elif hook in text:text=text.replace(hook,hook+'(()=>{'+helper+';registerFlincNotebookCommands(e)})();')
    else:raise ValueError('Cannot locate plugin activation')
    chunk.write_text(text)
    return rebuild_asset_names(root)


if __name__=='__main__':
    import sys
    print(patch(sys.argv[1]))
