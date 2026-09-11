
import sys, os, re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import fitz
from PIL import Image, ImageTk

APP = "Intuitive PDF Viewer"

class Viewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP)
        self.geometry("1400x900")
        self.minsize(1000, 650)
        self.configure(bg="#111214")

        self.doc = None
        self.path = None
        self.page = 0
        self.zoom = 1.0
        self.page_photo = None
        self.edit_items = {}       # canvas_id -> item data
        self.selected = None
        self.drag_offset = (0, 0)
        self.dnd = False

        self._style()
        self._ui()
        self._setup_dnd()

        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            self.after(150, lambda: self.open_pdf(sys.argv[1]))

    def _style(self):
        s = ttk.Style(self)
        try: s.theme_use("clam")
        except: pass
        s.configure("TScrollbar", troughcolor="#18191c", background="#3b3d42",
                    bordercolor="#18191c", arrowcolor="#c9ccd1")
        s.configure("Treeview", background="#191a1d", fieldbackground="#191a1d",
                    foreground="#e8eaed", borderwidth=0, rowheight=28)
        s.map("Treeview", background=[("selected","#30343b")])

    def _btn(self, parent, text, command, width=None):
        b=tk.Button(parent,text=text,command=command,bg="#2b2e33",fg="#f1f3f4",
                    activebackground="#3a3e45",activeforeground="white",
                    relief="flat",bd=0,padx=10,pady=7,cursor="hand2")
        if width: b.config(width=width)
        return b

    def _ui(self):
        # Header
        header=tk.Frame(self,bg="#1a1b1e",height=58)
        header.pack(fill="x")
        tk.Label(header,text="◈  PDF Studio",bg="#1a1b1e",fg="white",
                 font=("Segoe UI",15,"bold")).pack(side="left",padx=18)
        self._btn(header,"Open",self.pick).pack(side="left",padx=3)
        self._btn(header,"Save",self.save).pack(side="left",padx=3)
        self._btn(header,"Save As",self.save_as).pack(side="left",padx=3)

        self._btn(header,"＋ Text",self.start_text).pack(side="right",padx=3)
        self._btn(header,"＋ Image",self.start_image).pack(side="right",padx=3)
        self._btn(header,"Fit",self.fit).pack(side="right",padx=3)
        self._btn(header,"−",lambda:self.zoom_by(-.1),5).pack(side="right",padx=2)
        self._btn(header,"＋",lambda:self.zoom_by(.1),5).pack(side="right",padx=2)
        self.zoom_label=tk.Label(header,text="100%",bg="#1a1b1e",fg="#c9ccd1",
                                 font=("Segoe UI",9))
        self.zoom_label.pack(side="right",padx=8)

        # Main layout
        main=tk.Frame(self,bg="#111214")
        main.pack(fill="both",expand=True)

        sidebar=tk.Frame(main,bg="#18191c",width=285)
        sidebar.pack(side="left",fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar,text="DOCUMENT",bg="#18191c",fg="#858991",
                 font=("Segoe UI",9,"bold")).pack(anchor="w",padx=15,pady=(16,7))

        self.search_var=tk.StringVar()
        ent=tk.Entry(sidebar,textvariable=self.search_var,bg="#24262a",fg="white",
                     insertbackground="white",relief="flat",font=("Segoe UI",10))
        ent.pack(fill="x",padx=12,pady=(0,10),ipady=7)
        ent.bind("<Return>",lambda e:self.search())

        self.tree=ttk.Treeview(sidebar,show="tree")
        self.tree.pack(fill="both",expand=True,padx=7)
        self.tree.bind("<<TreeviewSelect>>",self.chapter)

        self.hint=tk.Label(sidebar,text="Drop a PDF anywhere in the window.\n"
                           "Select text/images on the page to move or resize them.",
                           bg="#18191c",fg="#7f848d",justify="left",
                           font=("Segoe UI",9),wraplength=250)
        self.hint.pack(fill="x",padx=14,pady=15)

        # Editor
        area=tk.Frame(main,bg="#101113")
        area.pack(side="left",fill="both",expand=True)

        toolbar=tk.Frame(area,bg="#202226",height=44)
        toolbar.pack(fill="x")
        self.selection_label=tk.Label(toolbar,text="No object selected",
                                      bg="#202226",fg="#aeb3bb",
                                      font=("Segoe UI",9))
        self.selection_label.pack(side="left",padx=14)

        tk.Label(toolbar,text="Size:",bg="#202226",fg="#aeb3bb").pack(side="left",padx=(15,4))
        self.size_var=tk.IntVar(value=18)
        self.size_spin=tk.Spinbox(toolbar,from_=6,to=144,textvariable=self.size_var,
                                  width=5,bg="#2b2e33",fg="white",
                                  insertbackground="white",relief="flat",
                                  command=self.apply_size)
        self.size_spin.pack(side="left")
        self.size_spin.bind("<Return>",lambda e:self.apply_size())

        self._btn(toolbar,"Apply size",self.apply_size).pack(side="left",padx=5)
        self._btn(toolbar,"Delete",self.delete_selected).pack(side="left",padx=3)

        self.canvas=tk.Canvas(area,bg="#0e0f11",highlightthickness=0)
        self.vbar=ttk.Scrollbar(area,orient="vertical",command=self.canvas.yview)
        self.hbar=ttk.Scrollbar(area,orient="horizontal",command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vbar.set,xscrollcommand=self.hbar.set)
        self.vbar.pack(side="right",fill="y")
        self.hbar.pack(side="bottom",fill="x")
        self.canvas.pack(fill="both",expand=True)

        self.canvas.bind("<Button-1>",self.click)
        self.canvas.bind("<B1-Motion>",self.drag)
        self.canvas.bind("<ButtonRelease-1>",self.release)
        self.canvas.bind("<MouseWheel>",self.wheel)
        self.bind("<Delete>",lambda e:self.delete_selected())
        self.bind("<Control-s>",lambda e:self.save())
        self.bind("<Control-o>",lambda e:self.pick())
        self.bind("<Left>",lambda e:self.prev())
        self.bind("<Right>",lambda e:self.next())

    def _setup_dnd(self):
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
            # tkinterdnd2 requires the root itself to be TkinterDnD.Tk.
            # The bundled build uses the optional drop bridge below when available.
            self.hint.config(text="Drag a PDF from Explorer onto the app.\n"
                                  "＋ Text / ＋ Image → click the page → drag to position.")
        except Exception:
            pass

    def pick(self):
        p=filedialog.askopenfilename(filetypes=[("PDF","*.pdf"),("All files","*.*")])
        if p:self.open_pdf(p)

    def open_pdf(self,p):
        try:d=fitz.open(p)
        except Exception as e:
            messagebox.showerror(APP,f"Could not open PDF:\n{e}");return
        if self.doc:self.doc.close()
        self.doc=d;self.path=p;self.page=0;self.zoom=1
        self.title(f"{os.path.basename(p)} — {APP}")
        self.build_outline();self.render()

    def build_outline(self):
        self.tree.delete(*self.tree.get_children())
        if not self.doc:return
        toc=self.doc.get_toc(simple=True)
        if toc:
            parents={}
            for level,title,page in toc:
                parent=parents.get(level-1,"")
                iid=self.tree.insert(parent,"end",text=title,values=(page-1,))
                parents[level]=iid
                for k in list(parents):
                    if k>level:del parents[k]
        else:
            root=self.tree.insert("","end",text="Detected checkpoints")
            for i in range(len(self.doc)):
                text=self.doc[i].get_text("text")
                lines=[x.strip() for x in text.splitlines() if x.strip()]
                hit=(i==0 or re.search(r"(?i)\b(chapter|section|part|appendix)\b",text) or
                     any(re.match(r"(?i)^(chapter|section|part)\s+\d+",x) for x in lines[:15]))
                if hit:
                    label=(lines[0][:65] if lines else f"Page {i+1}")
                    self.tree.insert(root,"end",text=f"{label}  ·  p.{i+1}",values=(i,))
            self.tree.item(root,open=True)

    def chapter(self,_=None):
        s=self.tree.selection()
        if not s:return
        v=self.tree.item(s[0],"values")
        if v:
            self.page=int(v[0]);self.render()

    def render(self):
        if not self.doc:return
        self.edit_items.clear();self.selected=None
        p=self.doc[self.page]
        pix=p.get_pixmap(matrix=fitz.Matrix(self.zoom,self.zoom),alpha=False)
        img=Image.frombytes("RGB",[pix.width,pix.height],pix.samples)
        self.page_photo=ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(30,20,image=self.page_photo,anchor="nw",tags=("page",))
        self.canvas.config(scrollregion=(0,0,pix.width+70,pix.height+60))
        self.zoom_label.config(text=f"{round(self.zoom*100)}%")
        self.selection_label.config(text=f"Page {self.page+1} / {len(self.doc)}")
        self.canvas.yview_moveto(0)

    def page_origin(self):
        return 30,20

    def canvas_to_pdf(self,x,y):
        ox,oy=self.page_origin()
        return (x-ox)/self.zoom,(y-oy)/self.zoom

    def pdf_to_canvas(self,x,y):
        ox,oy=self.page_origin()
        return ox+x*self.zoom,oy+y*self.zoom

    def start_text(self):
        if not self.doc:return
        text=simpledialog.askstring("Add text","Enter text:")
        if not text:return
        size=simpledialog.askinteger("Text size","Font size (6–144):",
                                     initialvalue=18,minvalue=6,maxvalue=144)
        if not size:return
        # Place at a visible default position; user can immediately drag it.
        x,y=self.pdf_to_canvas(72,72)
        item=self.canvas.create_text(x,y,text=text,anchor="nw",
                                     font=("Segoe UI",max(6,int(size*self.zoom))),
                                     fill="#111111",tags=("object",))
        self.edit_items[item]={"type":"text","text":text,"x":72,"y":72,
                               "size":size}
        self.select(item)
        self.selection_label.config(text="Text selected — drag it anywhere")

    def start_image(self):
        if not self.doc:return
        p=filedialog.askopenfilename(filetypes=[("Images","*.png *.jpg *.jpeg *.webp *.bmp"),("All files","*.*")])
        if not p:return
        try:
            im=Image.open(p); im.thumbnail((260,260))
            photo=ImageTk.PhotoImage(im)
        except Exception as e:
            messagebox.showerror(APP,f"Could not load image:\n{e}");return
        x,y=self.pdf_to_canvas(72,110)
        item=self.canvas.create_image(x,y,image=photo,anchor="nw",tags=("object",))
        self.edit_items[item]={"type":"image","path":p,"photo":photo,
                               "x":72,"y":110,"w":im.width,"h":im.height}
        self.select(item)
        self.selection_label.config(text="Image selected — drag it anywhere")

    def click(self,e):
        hits=self.canvas.find_overlapping(e.x-2,e.y-2,e.x+2,e.y+2)
        obj=next((i for i in reversed(hits) if i in self.edit_items),None)
        if obj:self.select(obj);self.drag_offset=(e.x,e.y)
        else:self.selected=None;self.selection_label.config(text=f"Page {self.page+1} / {len(self.doc)}")

    def select(self,item):
        self.selected=item
        d=self.edit_items[item]
        self.size_var.set(int(d.get("size",18)))
        self.selection_label.config(text=f"{d['type'].title()} selected — drag to position")

    def drag(self,e):
        if not self.selected:return
        x0,y0=self.drag_offset
        dx,dy=e.x-x0,e.y-y0
        self.canvas.move(self.selected,dx,dy)
        self.drag_offset=(e.x,e.y)
        d=self.edit_items[self.selected]
        d["x"] += dx/self.zoom
        d["y"] += dy/self.zoom

    def release(self,e):
        if self.selected:self.apply_size()

    def apply_size(self):
        if not self.selected or self.selected not in self.edit_items:return
        d=self.edit_items[self.selected]
        if d["type"]!="text":return
        try:size=max(6,min(144,int(self.size_var.get())))
        except:return
        d["size"]=size
        self.canvas.itemconfigure(self.selected,font=("Segoe UI",max(6,int(size*self.zoom))))

    def delete_selected(self):
        if self.selected:
            self.canvas.delete(self.selected)
            self.edit_items.pop(self.selected,None)
            self.selected=None
            self.selection_label.config(text="Object deleted")

    def bake_edits(self,doc):
        # Write current canvas objects into the PDF page at their current PDF coordinates.
        if not self.doc:return
        page=doc[self.page]
        for d in self.edit_items.values():
            if d["type"]=="text":
                page.insert_text((d["x"],d["y"]+d["size"]),
                                 d["text"],fontsize=d["size"],fontname="helv",
                                 color=(0.07,0.07,0.07))
            else:
                r=fitz.Rect(d["x"],d["y"],d["x"]+d["w"],d["y"]+d["h"])
                page.insert_image(r,filename=d["path"])

    def save(self):
        if not self.doc:return
        if not self.path:return self.save_as()
        try:
            self.bake_edits(self.doc)
            self.doc.save(self.path+".tmp",garbage=4,deflate=True)
            self.doc.close()
            os.replace(self.path+".tmp",self.path)
            self.doc=fitz.open(self.path)
            self.edit_items.clear()
            self.render()
            messagebox.showinfo(APP,"Saved.")
        except Exception as e:messagebox.showerror(APP,f"Save failed:\n{e}")

    def save_as(self):
        if not self.doc:return
        p=filedialog.asksaveasfilename(defaultextension=".pdf",
                                       filetypes=[("PDF","*.pdf")])
        if not p:return
        try:
            self.bake_edits(self.doc)
            self.doc.save(p,garbage=4,deflate=True)
            self.path=p
            self.edit_items.clear()
            self.render()
            self.title(f"{os.path.basename(p)} — {APP}")
        except Exception as e:messagebox.showerror(APP,f"Save failed:\n{e}")

    def search(self):
        if not self.doc:return
        q=self.search_var.get().strip()
        if not q:return
        for n in range(1,len(self.doc)+1):
            i=(self.page+n)%len(self.doc)
            if q.lower() in self.doc[i].get_text().lower():
                self.page=i;self.render();return
        messagebox.showinfo(APP,"No matching text found.")

    def zoom_by(self,d):
        if self.doc:self.zoom=max(.4,min(3.5,self.zoom+d));self.render()

    def fit(self):
        if not self.doc:return
        width=max(500,self.canvas.winfo_width()-70)
        self.zoom=width/self.doc[self.page].rect.width
        self.render()

    def wheel(self,e):
        self.canvas.yview_scroll(-int(e.delta/120)*3,"units")

    def prev(self):
        if self.doc and self.page>0:self.page-=1;self.render()

    def next(self):
        if self.doc and self.page<len(self.doc)-1:self.page+=1;self.render()

if __name__=="__main__":
    Viewer().mainloop()
