# 医用画像処理実験 最終課題

知能情報コース 22番 高垣俊佑

DICOMのAxial・Coronal・Sagittal表示、断面位置の連動、各面のWL/WW操作、肺マスクの3Dボリュームレンダリングを行うPythonアプリです。

## 1. 動作環境と導入

- 対象: Windows 10/11 x64、**CPython 3.12.x（64-bit）**。Python 3.12.10の公式Windowsインストーラを推奨します。
- Pythonは https://www.python.org/downloads/release/python-31210/ の「Windows installer (64-bit)」で導入できます。Python Launcher、pip、Tcl/Tkを含めてください。Python本体は同梱していません。
- RAM 8GB以上推奨。大きなシリーズでは画素数に応じてメモリを使用します。
- 同梱wheelはWindows x64・Python 3.12専用です。他のPython版やARM版では使用できません。
- アプリはネット接続不要です。Python導入後の依存パッケージ導入もオフラインで行えます。

### Windowsで起動（簡単な方法）

1. GitHubの **Code → Download ZIP** で取得し、**すべて展開**します。ZIP内から直接起動しないでください。
2. `setup_windows.bat` を実行します。同じフォルダに `.venv` が作成され、`vendor` のライブラリがインストールされます。
3. `Setup completed` が表示されたら、`start_windows.bat` を実行します。
4. 初回の確認は上部の **合成デモ** ボタンを押してください。

### コマンドから導入・起動

PowerShellでREADMEがあるフォルダを開いて実行します。仮想環境のactivateは不要です。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links=vendor -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

コンパイルは不要です。使用パッケージは `requirements.txt` に固定しています。TkinterはPython標準ライブラリです。

Linux/macOSで試す場合はPython 3.12、Tk、画面表示環境が必要です。同梱Windows wheelは使用せず `python -m pip install -r requirements.txt` で環境別のパッケージを取得してください。この場合はインターネットが必要です。

## 2. DICOM表示の操作

1. メニューバー **ファイル → DICOMフォルダを開く** を選択します。フォルダ内を再帰検索します。
2. または **DICOMファイルを選択** から同一シリーズの画像を複数選択します。拡張子がないDICOMにも対応します。
3. 複数シリーズがある場合はシリーズ一覧が表示されます。画像枚数と名称を確認して選択します。別シリーズを混ぜて積層しません。
4. Axial、Coronal、Sagittalが同時に表示されます。
5. 各面の **位置** スライダーを動かします。その画像と、他の2面に表示される対応する線が連動します。
6. **WL** はウィンドウ中心、**WW** は幅です。面ごとに独立して変更できます。`肺`・`軟部`・`骨`は表示条件のプリセットです。
7. 別のDICOMを開くと前の肺マスクを解除します。異なる画像のマスクを誤って残さないためです。

| 線の色 | 表す断面 | 表示される面 |
|---|---|---|
| 赤 | Axial | Coronal / Sagittal |
| 緑 | Coronal | Axial / Sagittal |
| 青 | Sagittal | Axial / Coronal |

方位表示は L=左、R=右、A=前、P=後、S=上、I=下です。Axialは画面左が患者右、上が前です。Coronalは上が頭側、画面左が患者右です。Sagittalは上が頭側、画面左が前です。

### 対応データと読み込み条件

- 非圧縮・単一フレーム・モノクロDICOM（MONOCHROME1/2）。同一シリーズ2枚以上。
- `ImagePositionPatient`、`ImageOrientationPatient`、`PixelSpacing`を使用して位置順を決定します。ファイル名順やInstanceNumberだけには依存しません。
- 患者座標に平行なAxial/Coronal/Sagittal方向を、内部のZ,Y,Xに並べ替えます。画素間隔を反映して縦横比を維持します。
- 各スライスにModality LUTまたはRescale Slope/Interceptを適用します。CTではHUへの変換になります。
- WL/WWはDICOMのLINEAR定義に従います。WW=1はしきい値処理です。元のVOI LUTテーブルやSIGMOID曲線は使用しません。
- 圧縮DICOM、Enhanced multi-frame、RGB、斜め断面、ガントリ傾斜、不等間隔、欠落・重複スライスは対応外としてエラーを表示します。
- 空フォルダ、画像以外のファイルは適切に扱い、読み込み失敗時は現在の表示を維持します。

## 3. 第5回の肺領域を3D表示（追加課題）

1. 第5回で作成した **背景0・肺領域が白（正の値）** の連続TIFFを用意します。
2. **ファイル → 肺マスクTIFFを開く** を選択します。
3. 1個の複数ページTIFF、または複数の2D TIFFを読み込めます。複数ファイルはファイル名の数値順（1,2,…,10）に並べます。
4. TIFFの配列は **Z,Y,X** とします。Zは下→上、Yは前→後、Xは患者右→左の順にしてください。ImageJでの並びが逆なら元の処理で反転してください。TIFFに患者座標情報がないため自動判定できません。
5. **間隔 mm (Z,Y,X)** に元DICOMのスライス間隔、行方向画素間隔、列方向画素間隔を入力します。DICOMを開いた場合はその値が入りますが、異なるデータやリサイズしたマスクでは必ず修正してください。TIFFだけの場合は1mmが初期値です。
6. **3D更新** を押すとボリュームレンダリングします。回転・上下・不透明度を変更し、再度 **3D更新** を押してください。

描画はCPUによる直交投影のレイキャスティングです。視線上のボクセルを手前から奥へたどり、色と不透明度を合成します。ポリゴン表面だけの描画ではありません。処理負荷を抑えるため出力280×280画素、視線方向最大400サンプルの簡易描画であり、細い構造は失われる場合があります。3Dは更新ボタンで再計算し、処理中もウィンドウは応答します。

**同梱の `demo/synthetic_lung_mask.tif` は動作確認用の合成ファントムです。第5回の抽出結果ではありません。第5回の実データは今回の添付資料に含まれていないため同梱していません。追加課題の評価を受ける際は、自分の第5回のTIFFを本機能で表示して確認してください。**

## 4. 採点観点との対応

| 観点 | 実装・確認方法 |
|---|---|
| 1 スライスViewer | `app.py`の3つのCanvasで表示 |
| 2 ファイルメニュー | DICOMフォルダ・複数ファイルを選択 |
| 3 3方向 | `core.py`の患者座標正規化と `plane()` |
| 4 他の2断面の線 | 各画像上に2色の断面線 |
| 5 WL/WW/位置スライダー | 各面に3本ずつ配置 |
| 6 線の連動 | 共有位置から全画像・線を再描画 |
| 7 肺の3D表示 | 連続TIFFの読み込みとレイキャスティング。授業の肺マスクは別途必要 |

GitHubから取得した場合、合成デモのファイルは初回の「合成デモ」操作で自動生成します。

## 5. ファイル構成

- `app.py`: GUI、ファイルメニュー、スライダー、表示更新
- `core.py`: DICOM読み込み・整列・方向補正、WL/WW、3D計算
- `requirements.txt`: 依存パッケージの固定バージョン
- `vendor/`: Windows x64/Python 3.12用ライブラリのwheel
- `setup_windows.bat` / `start_windows.bat`: 導入・起動
- `demo/dicom/`: 合成DICOM 48枚
- `demo/synthetic_lung_mask.tif`: 合成肺マスク
- `make_demo.py`: 合成データ生成コード
- `test_core.py`: 計算と入力検証の自動テスト
- `VALIDATION.md`: 検証結果と制限
- `THIRD_PARTY.md`: 同梱ライブラリとライセンス案内

## 6. テスト

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_core
```

GUIではデモを開き、各位置を端まで動かして線の連動を確認します。WL/WWを変えて濃淡が変わること、各面で独立して変更できること、3Dの角度・不透明度が変化することを確認します。

## 7. エラーへの対処

- `py`が見つからない: Python 3.12とPython Launcherをインストールしてください。
- `No matching distribution`: Python 3.12の64-bit版であることとvendorが展開済みであることを確認してください。
- `No module named ...`: `setup_windows.bat`を実行し、`start_windows.bat`から起動してください。
- `_tkinter`のエラー: 公式Pythonのインストールを変更しTcl/Tkを有効にしてください。
- `圧縮DICOMには未対応`: 元データを非圧縮DICOMに変換してから開いてください。
- `欠落・重複・不等間隔`: 同じ位置の別再構成画像を混ぜず、連続した1シリーズを選択してください。
- 3Dが細長い・上下逆: 元CTの画素間隔とマスクのZ順を確認してください。

## 8. GitHubへの提出

新しいリポジトリにこのフォルダの内容を登録します。`vendor`も必要なので除外しないでください。`.venv`や実患者データは登録しません。教員が閲覧できる公開リポジトリ（または教員にアクセス権を付与した非公開リポジトリ）で、Code → Download ZIPが使用できることを確認してから、授業の提出欄へ **リポジトリのURL** を提出してください。

## 9. 実装参考

- DICOM PS3.3 C.11.2（WL/WW）: https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.11.2.html
- pydicom Working with Pixel Data: https://pydicom.github.io/pydicom/stable/guides/user/working_with_pixel_data.html

教育用の課題アプリであり、診断用医療機器ではありません。
