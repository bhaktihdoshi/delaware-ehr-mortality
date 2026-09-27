"""Execute the project notebooks with the active Python environment."""
import os
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager
import tempfile,json,sys

root=Path(__file__).resolve().parents[1]
# Temporary kernel registration avoids modifying the user's Jupyter installation.
with tempfile.TemporaryDirectory() as directory:
    kernel=Path(directory)/'kernels'/'portfolio'; kernel.mkdir(parents=True)
    (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Portfolio','language':'python'}))
    os.environ['JUPYTER_PATH']=directory+os.pathsep+os.environ.get('JUPYTER_PATH','')
    for filename in ['assessment.ipynb','results_review.ipynb']:
        path=root/'notebooks'/filename
        notebook=nbformat.read(path,as_version=4)
        NotebookClient(notebook,timeout=300,kernel_name='portfolio',resources={'metadata':{'path':str(root)}}).execute()
        notebook.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
        nbformat.write(notebook,path)
        print(f'Executed {filename}',flush=True)
