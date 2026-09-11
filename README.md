# Intuitive PDF Viewer v2

Modern dark PDF viewer/editor.

## New
- Modernized interface
- Choose text size when inserting
- Change selected text size from the toolbar
- Click + drag text anywhere on the page
- Click + drag images anywhere on the page
- Delete selected text/images
- Save / Save As with edits baked into the PDF
- Existing PDF chapters/TOC shown in sidebar
- Automatic checkpoint detection when no TOC exists
- Search, zoom, fit, keyboard navigation

## Build the Windows EXE

On Windows:
```bat
py -m pip install -r requirements.txt
py -m PyInstaller --onefile --windowed --name IntuitivePDFViewer pdf_viewer.py
```

The EXE will be in `dist\IntuitivePDFViewer.exe`.

For Explorer drag/drop, the source can be upgraded to a TkinterDnD root if desired; opening a PDF by dragging it onto the EXE also works by passing it as the EXE argument.
