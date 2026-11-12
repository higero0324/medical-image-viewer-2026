"""Medical image processing final assignment: Tk MPR viewer + lung volume view."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import numpy as np
from PIL import Image, ImageTk
from core import scan_series, load_series, window_image, plane, read_mask, render_volume

BASE = Path(__file__).resolve().parent
COLORS = ('#ff818a', '#6ee7b7', '#7db6ff')
NAMES = ('Axial / 横断面', 'Coronal / 冠状断面', 'Sagittal / 矢状断面')

class Viewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('医用画像処理実験 最終課題 | I22 高垣俊佑')
        self.geometry('1280x850'); self.minsize(980, 700)
        self.configure(bg='#101827')
        style=ttk.Style(self); style.theme_use('clam')
        style.configure('TFrame',background='#101827')
        style.configure('TLabel',background='#101827',foreground='#e4edf7',font=('',10))
        style.configure('TLabelframe',background='#101827')
        style.configure('TLabelframe.Label',background='#101827',foreground='#e4edf7')
        self.volume=None;self.mask=None;self.photos={};self.jobs=queue.Queue();self.busy=False
        self.position=[tk.IntVar(value=0) for _ in range(3)]
        self.wl=[tk.IntVar(value=-600) for _ in range(3)]
        self.ww=[tk.IntVar(value=1500) for _ in range(3)]
        self.status=tk.StringVar(value='ファイル → DICOMフォルダを開く、またはデモを開く')
        menu=tk.Menu(self); fm=tk.Menu(menu,tearoff=False)
        fm.add_command(label='DICOMフォルダを開く…',command=self.open_folder)
        fm.add_command(label='DICOMファイルを選択…',command=self.open_files)
        fm.add_separator();fm.add_command(label='肺マスクTIFFを開く…',command=self.open_mask)
        fm.add_command(label='合成デモを開く',command=self.open_demo)
        fm.add_separator();fm.add_command(label='終了',command=self.destroy)
        menu.add_cascade(label='ファイル',menu=fm)
        menu.add_command(label='操作説明',command=lambda: messagebox.showinfo('操作説明','DICOMを開くと3方向を表示します。\n各パネルの位置・WL・WWを調整してください。\n赤=Axial、緑=Coronal、青=Sagittalの断面位置です。\n3Dは肺マスクTIFFを読み込み、画素間隔を設定し「3D更新」を押します。\n詳細は同梱README.mdを参照してください。'))
        self.config(menu=menu)
        top=ttk.Frame(self);top.pack(fill='x',padx=16,pady=10)
        ttk.Label(top,text='MEDICAL IMAGE VIEWER',font=('',18,'bold')).pack(side='left')
        ttk.Button(top,text='DICOMを開く',command=self.open_folder).pack(side='right',padx=5)
        ttk.Button(top,text='合成デモ',command=self.open_demo).pack(side='right',padx=5)
        grid=ttk.Frame(self);grid.pack(fill='both',expand=True,padx=12)
        for i in range(2):grid.rowconfigure(i,weight=1);grid.columnconfigure(i,weight=1)
        self.canvases=[];self.scales=[];self.labels=[]
        for axis in range(3):
            box=ttk.LabelFrame(grid,text=NAMES[axis],padding=8);box.grid(row=axis//2,column=axis%2,sticky='nsew',padx=4,pady=4)
            canvas=tk.Canvas(box,bg='#060b12',highlightthickness=0,height=190)
            canvas.pack(fill='both',expand=True)
            canvas.bind('<Configure>',lambda e:self.draw_all())
            self.canvases.append(canvas)
            row=[];labs=[]
            for title,var,low,high in [('位置',self.position[axis],0,1),('WL',self.wl[axis],-2000,3000),('WW',self.ww[axis],1,5000)]:
                line=ttk.Frame(box);line.pack(fill='x')
                ttk.Label(line,text=title,width=5).pack(side='left')
                label=ttk.Label(line,width=17);label.pack(side='right');labs.append(label)
                scale=tk.Scale(line,from_=low,to=high,variable=var,orient='horizontal',showvalue=False,
                               bg='#101827',fg='white',highlightthickness=0,troughcolor='#2b3b52',
                               command=lambda value:self.draw_all(),resolution=1)
                scale.pack(side='left',fill='x',expand=True);row.append(scale)
            presets=ttk.Frame(box);presets.pack(fill='x')
            for label,l,w in [('肺',-600,1500),('軟部',40,400),('骨',400,1800)]:
                ttk.Button(presets,text=label,command=lambda a=axis,l=l,w=w:self.preset(a,l,w)).pack(side='left',padx=2)
            self.scales.append(row);self.labels.append(labs)
        box=ttk.LabelFrame(grid,text='Lung / 3D volume rendering',padding=8)
        box.grid(row=1,column=1,sticky='nsew',padx=4,pady=4)
        self.canvas3=tk.Canvas(box,bg='#060b12',height=190,highlightthickness=0);self.canvas3.pack(fill='both',expand=True)
        self.canvas3.bind('<Configure>',self.redraw3)
        self.rendered=None
        self.yaw=tk.IntVar(value=25);self.pitch=tk.IntVar(value=10);self.opacity=tk.DoubleVar(value=.06)
        controls=ttk.Frame(box);controls.pack(fill='x')
        for name,var,lo,hi,res in [('回転',self.yaw,-180,180,1),('上下',self.pitch,-90,90,1),('不透明度',self.opacity,.005,.3,.005)]:
            f=ttk.Frame(controls);f.pack(side='left',expand=True,fill='x')
            ttk.Label(f,text=name).pack()
            tk.Scale(f,from_=lo,to=hi,resolution=res,variable=var,orient='horizontal',length=120,
                     bg='#101827',fg='white',highlightthickness=0).pack(fill='x')
        line=ttk.Frame(box);line.pack(fill='x')
        ttk.Label(line,text='間隔 mm (Z,Y,X)').pack(side='left')
        self.spacing_vars=[tk.StringVar(value='1') for _ in range(3)]
        for var in self.spacing_vars:ttk.Entry(line,textvariable=var,width=6).pack(side='left',padx=2)
        ttk.Button(line,text='TIFFを開く',command=self.open_mask).pack(side='right')
        ttk.Button(line,text='3D更新',command=self.update3).pack(side='right',padx=4)
        self.mask_info=tk.StringVar(value='背景0・肺領域が白の連続TIFFを選択')
        ttk.Label(box,textvariable=self.mask_info).pack(fill='x',pady=3)
        ttk.Label(self,textvariable=self.status,wraplength=1200).pack(fill='x',padx=16,pady=8)
        self.after(80,self.poll)

    def run_task(self,task,done):
        if self.busy:
            messagebox.showinfo('処理中','現在の処理が終わるまでお待ちください。');return
        self.busy=True;self.status.set('処理中…')
        def worker():
            try:self.jobs.put((done,task(),None))
            except Exception as exc:self.jobs.put((done,None,exc))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            done,result,error=self.jobs.get_nowait();self.busy=False
            if error:
                self.status.set('エラー: '+str(error));messagebox.showerror('読み込み・処理エラー',str(error))
            else:done(result)
        except queue.Empty:pass
        self.after(80,self.poll)

    def open_folder(self):
        folder=filedialog.askdirectory(title='DICOMシリーズを含むフォルダ')
        if folder:self.scan(list(Path(folder).rglob('*')))

    def open_files(self):
        paths=filedialog.askopenfilenames(title='同一シリーズのDICOMを複数選択',filetypes=[('すべてのファイル','*')])
        if paths:self.scan(paths)

    def scan(self,paths):
        self.run_task(lambda:scan_series([p for p in paths if Path(p).is_file()]),self.select_series)

    def select_series(self,result):
        groups,skipped=result
        if len(groups)==1:
            self.run_task(lambda:load_series(next(iter(groups.values()))),self.set_volume);return
        dialog=tk.Toplevel(self);dialog.title('シリーズを選択');dialog.geometry('700x300');dialog.grab_set()
        choices=list(groups.values());lst=tk.Listbox(dialog,width=90);lst.pack(fill='both',expand=True,padx=8,pady=8)
        for entries in choices:
            ds=entries[0][1];lst.insert('end',f'{getattr(ds,"SeriesDescription","名称なし")} | {len(entries)}枚 | Series {getattr(ds,"SeriesNumber","?")} | {ds.SeriesInstanceUID}')
        lst.selection_set(0)
        def choose():
            if not lst.curselection():return
            entries=choices[lst.curselection()[0]];dialog.destroy()
            self.run_task(lambda:load_series(entries),self.set_volume)
        ttk.Button(dialog,text='選択したシリーズを読み込む',command=choose).pack(pady=8)
        self.status.set(f'{len(groups)}シリーズを検出。画像以外のファイル {skipped}件を除外。')

    def set_volume(self,volume):
        self.volume=volume
        # Do not retain an unrelated previous patient's mask.
        self.mask=None;self.rendered=None;self.canvas3.delete('all')
        self.mask_info.set('肺マスク未選択（3D表示にはTIFFを開いてください）')
        lo=float(volume.data.min());hi=float(volume.data.max())
        for axis,n in enumerate(volume.data.shape):
            self.scales[axis][0].configure(to=n-1)
            self.position[axis].set(n//2)
            self.scales[axis][1].configure(from_=int(min(-2000,lo)),to=int(max(3000,hi)))
            self.scales[axis][2].configure(to=int(max(5000,hi-lo+1)))
            self.wl[axis].set(-600);self.ww[axis].set(1500)
        for var,value in zip(self.spacing_vars,volume.spacing):var.set(f'{value:g}')
        self.status.set(f'{volume.name} | Z,Y,X={volume.data.shape} | 間隔={tuple(round(v,3) for v in volume.spacing)} mm')
        self.draw_all()

    def preset(self,axis,level,width):
        self.wl[axis].set(level);self.ww[axis].set(width);self.draw_all()

    def draw_all(self):
        if self.volume is None:return
        position=[v.get() for v in self.position]
        if any(p<0 or p>=n for p,n in zip(position,self.volume.data.shape)):return
        for axis,canvas in enumerate(self.canvases):
            values,spacing,cross=plane(self.volume,axis,position)
            pix=window_image(values,self.wl[axis].get(),self.ww[axis].get(),self.volume.inverted)
            h,w=pix.shape;cw=max(canvas.winfo_width(),10);ch=max(canvas.winfo_height(),10)
            scale=min(cw/(w*spacing[1]),ch/(h*spacing[0]))
            iw=max(1,round(w*spacing[1]*scale));ih=max(1,round(h*spacing[0]*scale))
            photo=ImageTk.PhotoImage(Image.fromarray(pix).resize((iw,ih),Image.Resampling.NEAREST))
            self.photos[axis]=photo;canvas.delete('all');ox=(cw-iw)/2;oy=(ch-ih)/2
            canvas.create_image(ox,oy,image=photo,anchor='nw')
            cx=ox+(cross[0]+.5)*iw/w;cy=oy+(cross[1]+.5)*ih/h
            vertical,horizontal=((2,1),(2,0),(1,0))[axis]
            canvas.create_line(cx,oy,cx,oy+ih,fill=COLORS[vertical],width=1)
            canvas.create_line(ox,cy,ox+iw,cy,fill=COLORS[horizontal],width=1)
            for tx,ty,label in [(cw/2,12,('A','S','S')[axis]),(cw/2,ch-12,('P','I','I')[axis]),(12,ch/2,('R','R','A')[axis]),(cw-12,ch/2,('L','L','P')[axis])]:
                canvas.create_text(tx,ty,text=label,fill='white')
            self.labels[axis][0].config(text=f'{position[axis]+1} / {self.volume.data.shape[axis]}')
            self.labels[axis][1].config(text=str(self.wl[axis].get()))
            self.labels[axis][2].config(text=str(self.ww[axis].get()))

    def open_demo(self):
        def task():
            folder=BASE/'demo'
            if not (folder/'dicom').exists():
                from make_demo import generate
                generate(folder)
            groups,_=scan_series(sorted((folder/'dicom').glob('*.dcm')))
            return load_series(next(iter(groups.values()))),read_mask([folder/'synthetic_lung_mask.tif'])
        def done(result):
            self.set_volume(result[0]);self.mask=result[1]
            self.mask_info.set('合成肺ファントム（第5回の抽出結果ではありません）');self.update3()
        self.run_task(task,done)

    def open_mask(self):
        paths=filedialog.askopenfilenames(title='連続TIFFまたは番号順のTIFF画像群',filetypes=[('TIFF','*.tif *.tiff'),('すべて','*')])
        if not paths:return
        def done(mask):
            self.mask=mask;self.rendered=None;self.canvas3.delete('all')
            self.mask_info.set(f'マスク Z,Y,X={mask.shape} | 白={mask.sum():,} voxel')
            self.status.set('TIFFを読み込みました。Z,Y,Xの間隔・スライス順をREADMEで確認し「3D更新」を押してください。')
        self.run_task(lambda:read_mask(paths),done)

    def update3(self):
        if self.mask is None:
            messagebox.showinfo('マスク未選択','ファイル → 肺マスクTIFFを開く を選んでください。');return
        try:
            spacing=tuple(float(v.get()) for v in self.spacing_vars)
            if not np.isfinite(spacing).all() or min(spacing)<=0:raise ValueError()
        except ValueError:
            messagebox.showerror('間隔','Z,Y,Xに正の有限値を入力してください。');return
        mask=self.mask;args=(self.yaw.get(),self.pitch.get(),self.opacity.get())
        self.run_task(lambda:render_volume(mask,spacing,*args),self.set_render)

    def set_render(self,pixels):
        self.rendered=Image.fromarray(pixels);self.redraw3()
        self.status.set('3D描画完了。回転・上下・不透明度を変更し「3D更新」で再描画できます。')

    def redraw3(self,event=None):
        if self.rendered is None:return
        size=max(1,min(self.canvas3.winfo_width(),self.canvas3.winfo_height()))
        self.photos[3]=ImageTk.PhotoImage(self.rendered.resize((size,size),Image.Resampling.BILINEAR))
        self.canvas3.delete('all');self.canvas3.create_image(self.canvas3.winfo_width()/2,self.canvas3.winfo_height()/2,image=self.photos[3])

if __name__=='__main__':
    Viewer().mainloop()
