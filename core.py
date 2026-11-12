"""DICOM volume loading, orthogonal MPR and CPU volume ray casting."""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pydicom
from pydicom.pixels import apply_modality_lut
import tifffile

@dataclass
class Volume:
    data: np.ndarray  # canonical [superior, posterior, left], increasing LPS
    spacing: tuple   # z, y, x (mm)
    name: str
    inverted: bool = False


def scan_series(paths):
    groups, skipped = {}, 0
    for path in paths:
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True)
            if not hasattr(ds, 'Rows') or not hasattr(ds, 'SeriesInstanceUID'):
                skipped += 1
                continue
            key = str(ds.SeriesInstanceUID)
            groups.setdefault(key, []).append((str(path), ds))
        except (pydicom.errors.InvalidDicomError, OSError, ValueError):
            skipped += 1
    if not groups:
        raise ValueError('読み込めるDICOM画像がありません。ZIPは先に展開してください。')
    return groups, skipped


def load_series(entries):
    if len(entries) < 2:
        raise ValueError('3方向表示には同一シリーズの2枚以上のスライスが必要です。')
    ref = entries[0][1]
    required = ('ImageOrientationPatient', 'ImagePositionPatient', 'PixelSpacing')
    if any(not hasattr(ref, tag) for tag in required):
        raise ValueError('位置・方向・画素間隔のDICOMタグが必要です。')
    orient = np.asarray(ref.ImageOrientationPatient, dtype=float)
    col, row = orient[:3], orient[3:]
    normal = np.cross(col, row)
    basis = np.column_stack((normal, row, col))
    axes = np.argmax(np.abs(basis), axis=0)
    if len(set(axes)) != 3 or not np.allclose(basis.T @ basis, np.eye(3), atol=1e-4) or not np.allclose(np.abs(basis).max(axis=0), 1, atol=1e-4):
        raise ValueError('斜め撮影には未対応です。患者座標軸に平行なシリーズを選択してください。')
    ps = np.asarray(ref.PixelSpacing, float)
    if not np.all(np.isfinite(ps)) or np.any(ps <= 0):
        raise ValueError('PixelSpacingが不正です。')
    ordered = []
    photo = str(ref.PhotometricInterpretation)
    for path, ds in entries:
        if any(not hasattr(ds, tag) for tag in required):
            raise ValueError('一部のスライスに位置情報がありません。')
        if int(getattr(ds, 'NumberOfFrames', 1)) != 1 or int(ds.SamplesPerPixel) != 1:
            raise ValueError('単一フレームのモノクロDICOMのみ対応しています。')
        if str(ds.PhotometricInterpretation) != photo or photo not in ('MONOCHROME1', 'MONOCHROME2'):
            raise ValueError('モノクロ画像の形式が一致しません。')
        if (int(ds.Rows), int(ds.Columns)) != (int(ref.Rows), int(ref.Columns)):
            raise ValueError('同じシリーズ内に異なる画像サイズがあります。')
        if not np.allclose(ds.ImageOrientationPatient, orient, atol=1e-4) or not np.allclose(ds.PixelSpacing, ps):
            raise ValueError('方向または画素間隔が不均一です。')
        position = np.asarray(ds.ImagePositionPatient, float)
        if not np.isfinite(position).all():
            raise ValueError('スライス位置が不正です。')
        ordered.append((float(position @ normal), position, path))
    ordered.sort(key=lambda item: item[0])
    distances = np.diff([item[0] for item in ordered])
    dz = float(np.median(distances))
    if dz <= 0 or not np.allclose(distances, dz, rtol=.02, atol=.01):
        raise ValueError('スライス位置の重複・欠落・不等間隔があります。別シリーズを選択してください。')
    offsets = np.array([item[1] for item in ordered]) - ordered[0][1]
    if np.max(np.abs(offsets @ col)) > .05 or np.max(np.abs(offsets @ row)) > .05:
        raise ValueError('ガントリ傾斜または位置ずれのあるシリーズには未対応です。')
    frames = []
    for _, _, path in ordered:
        ds = pydicom.dcmread(path)
        if ds.file_meta.TransferSyntaxUID.is_compressed:
            raise ValueError('圧縮DICOMには未対応です。非圧縮DICOMを使用してください。')
        frames.append(apply_modality_lut(ds.pixel_array, ds).astype(np.float32))
    data = np.stack(frames)
    # Source axes are stack,row,column; destination axes are S,P,L.
    permutation = [list(axes).index(axis) for axis in (2, 1, 0)]
    data = data.transpose(permutation)
    spacing = np.array([dz, ps[0], ps[1]])[permutation]
    for dst, src in enumerate(permutation):
        if basis[axes[src], src] < 0:
            data = np.flip(data, axis=dst)
    if not np.isfinite(data).all():
        raise ValueError('画素値に非数値が含まれています。')
    return Volume(np.ascontiguousarray(data), tuple(spacing),
                  str(getattr(ref, 'SeriesDescription', 'DICOM series')), photo == 'MONOCHROME1')


def window_image(values, level, width, inverted=False):
    """DICOM LINEAR VOI with the defined half-unit offset and WW=1 threshold."""
    width = max(float(width), 1)
    if width == 1:
        output = (values > level - .5).astype(np.uint8) * 255
    else:
        output = (np.clip((values - (level - .5)) / (width - 1) + .5, 0, 1) * 255).astype(np.uint8)
    return 255 - output if inverted else output


def plane(volume, axis, position):
    z, y, x = position
    if axis == 0:
        return volume.data[z], (volume.spacing[1], volume.spacing[2]), (x, y)
    if axis == 1:
        return volume.data[::-1, y, :], (volume.spacing[0], volume.spacing[2]), (x, volume.data.shape[0]-1-z)
    return volume.data[::-1, :, x], (volume.spacing[0], volume.spacing[1]), (y, volume.data.shape[0]-1-z)


def read_mask(paths):
    if len(paths) == 1:
        data = tifffile.imread(paths[0])
    else:
        import re
        def natural(p):
            return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', Path(p).name)]
        data = np.stack([tifffile.imread(p) for p in sorted(paths, key=natural)])
    if data.ndim != 3 or min(data.shape) < 2:
        raise ValueError('マスクは [スライス, 高さ, 幅] の3次元TIFFにしてください。')
    if not np.isfinite(data).all():
        raise ValueError('マスクに非数値があります。')
    mask = data > 0
    if not mask.any() or mask.all():
        raise ValueError('背景0・肺領域が正の値の二値マスクを選択してください。')
    return mask


def render_volume(mask, spacing, yaw=25, pitch=10, opacity=.06, size=280):
    """Orthographic front-to-back emission/absorption ray casting, not a mesh."""
    spacing = np.asarray(spacing, float)
    if spacing.shape != (3,) or not np.isfinite(spacing).all() or np.any(spacing <= 0):
        raise ValueError('Z,Y,Xの画素間隔には正の有限値を入力してください。')
    extent = np.maximum(np.array(mask.shape)-1, 1) * spacing
    radius = np.linalg.norm(extent) / 2
    a, b = np.deg2rad([yaw, pitch])
    ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    rot = ry @ rx
    screen = np.linspace(-radius, radius, size, dtype=np.float32)
    xx, yy = np.meshgrid(screen, screen)
    # World axes x=L, y=P, z=S. Screen top corresponds to +S.
    base = np.stack((xx, np.zeros_like(xx), -yy), axis=-1) @ rot.T
    direction = np.array([0., 1., 0.]) @ rot.T
    rgb = np.zeros((size, size, 3), np.float32)
    alpha = np.zeros((size, size), np.float32)
    steps = min(400, max(80, int(2 * radius / min(spacing)) + 1))
    step_mm = 2 * radius / (steps-1)
    voxel_alpha = 1 - np.exp(-float(opacity) * step_mm)
    for t in np.linspace(-radius, radius, steps):
        coords = base + t * direction
        index = np.rint((coords[..., ::-1] + extent/2) / spacing).astype(np.int32)
        inside = np.all((index >= 0) & (index < np.array(mask.shape)), axis=-1)
        hit = np.zeros_like(inside)
        q = index[inside]
        hit[inside] = mask[q[:, 0], q[:, 1], q[:, 2]]
        weight = (1-alpha) * hit * voxel_alpha
        # Depth cueing preserves internal volume contributions.
        color = np.array([.40, .82, 1.]) * (1 - .4 * (t+radius)/(2*radius))
        rgb += weight[..., None] * color
        alpha += weight
    rgb += (1-alpha[..., None]) * np.array([.025, .04, .065])
    return np.uint8(np.clip(rgb * 255, 0, 255))
