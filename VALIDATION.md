# 検証記録

## 実行環境

Python 3.12.14 / Linux x86_64。新規仮想環境を作成し、requirements.txtに記載したNumPy 2.2.6、Pillow 11.3.0、pydicom 3.0.1、tifffile 2025.5.10のみをインストールして検証しました。

## 自動検証

`python -m unittest -v test_core`: 10テスト成功。

- DICOM入力順が逆でも撮影位置で整列する
- 読み込み後の画素値・画素間隔が合成元と一致する
- 3方向の交差点が同一ボクセルに一致する
- WL/WW変換がpydicomの参照実装と一致する
- WW=1、白黒反転
- 重複、欠落、斜め撮影、マルチフレームの拒否
- 方向反転とRescale Slope/Intercept適用
- TIFFマスク読み込み、3Dの角度・不透明度変更による出力変化

`python -m pip check`: 依存関係の不整合なし。
Python構文コンパイル確認済み。同梱wheelのZIP整合性を確認済み。

## 検証範囲と残る確認

- 計算処理は合成DICOMと合成マスクで検証しています。第5回の実CT・実肺マスクは今回未提供であり、実データ検証は未実施です。
- Windows実機でのBAT実行・Tk画面操作は未検証です。検証環境では画面サーバーへの接続が制限され、GUI実起動を確認できませんでした。
- Windows用wheelはPython 3.12・win_amd64タグを持つ公式PyPI配布物です。Windowsで `setup_windows.bat` → `start_windows.bat` → `合成デモ` を実行し、提出前に動作を確認してください。
- 圧縮DICOM、斜め断面、Enhanced multi-frame、欠落・不等間隔シリーズは対応外です。
- 追加課題はTIFFを3D描画する機能を実装していますが、同梱マスクは第5回の成果物の代替ではありません。
