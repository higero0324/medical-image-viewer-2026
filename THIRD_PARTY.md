# 同梱ライブラリ

Windows x64 / CPython 3.12向けwheelをPyPIから取得して `vendor/` に同梱しています。各wheelはZIP形式で、ライセンス本文・著作権表示は内部の `.dist-info` 配下に含まれています。再配布時もwheelをそのまま保持してください。

| ライブラリ | バージョン | 主なライセンス |
|---|---|---|
| NumPy | 2.2.6 | BSD-3-Clause。バイナリに含まれる依存物のライセンスもwheel内に収録 |
| Pillow | 11.3.0 | MIT-CMU。付属依存物についてはwheel内のライセンス参照 |
| pydicom | 3.0.1 | MIT |
| tifffile | 2025.5.10 | BSD-3-Clause |

Python本体は同梱していません。デモDICOM・デモマスクは `make_demo.py` で生成した合成データです。実患者の画像や個人情報は含みません。
