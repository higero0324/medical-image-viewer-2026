"""Run: python -m unittest -v test_core"""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pydicom
from pydicom.pixels import apply_windowing
from make_demo import generate
from core import scan_series,load_series,window_image,plane,read_mask,render_volume

class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.hu,cls.mask=generate(cls.root)
        groups,_=scan_series(list((cls.root/'dicom').glob('*'))[::-1])
        cls.entries=next(iter(groups.values()));cls.vol=load_series(cls.entries)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_position_sort_rescale(self):
        np.testing.assert_array_equal(self.vol.data,self.hu)
        self.assertEqual(self.vol.spacing,(3.,2.,2.))
    def test_mpr_crosshair_coordinates(self):
        pos=(7,22,31)
        for axis in range(3):
            p,spacing,(x,y)=plane(self.vol,axis,pos)
            self.assertEqual(p[y,x],self.vol.data[pos])
        self.assertEqual(plane(self.vol,1,pos)[0].shape,(48,96))
        self.assertEqual(plane(self.vol,2,pos)[0].shape,(48,80))
    def test_window_against_pydicom(self):
        ds=pydicom.dcmread(self.entries[0][0]);ds.WindowCenter=40;ds.WindowWidth=400
        values=np.array([-1024,-160,-159,0,40,239,240,2000],np.float32)
        reference=(apply_windowing(values,ds)+32768)/65535*255
        np.testing.assert_allclose(window_image(values,40,400),reference,atol=1)
    def test_width_one_and_inversion(self):
        a=np.array([-.6,-.5,0,1])
        np.testing.assert_array_equal(window_image(a,0,1),[0,0,255,255])
        np.testing.assert_array_equal(window_image(a,0,1,True),[255,255,0,0])
    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError,'重複'):
            load_series(self.entries+[self.entries[0]])
    def test_missing_slice_rejected(self):
        entries=sorted(self.entries,key=lambda p:float(p[1].ImagePositionPatient[2]))
        with self.assertRaisesRegex(ValueError,'欠落'):load_series(entries[:8]+entries[9:])
    def test_oblique_rejected(self):
        import copy
        entries=copy.deepcopy(self.entries)
        entries[0][1].ImageOrientationPatient=[.7071,.7071,0,-.7071,.7071,0]
        with self.assertRaisesRegex(ValueError,'斜め'):load_series(entries)
    def test_mask_and_ray_cast(self):
        mask=read_mask([self.root/'synthetic_lung_mask.tif'])
        np.testing.assert_array_equal(mask,self.mask)
        a=render_volume(mask,(3,2,2),size=64)
        b=render_volume(mask,(3,2,2),yaw=80,size=64)
        self.assertEqual(a.shape,(64,64,3));self.assertGreater(a.max(),50)
        self.assertFalse(np.array_equal(a,b))
        c=render_volume(mask,(3,2,2),opacity=.2,size=64)
        self.assertGreater(float(c.mean()),float(a.mean()))
    def test_orientation_flip_and_rescale(self):
        root=self.root/'flipped';generate(root)
        for path in (root/'dicom').glob('*'):
            ds=pydicom.dcmread(path)
            ds.ImageOrientationPatient=[-1,0,0,0,1,0]
            ds.ImagePositionPatient[0]=190
            ds.PixelData=ds.pixel_array[:,::-1].astype('<i2').tobytes()
            ds.RescaleSlope=2;ds.RescaleIntercept=10
            ds.save_as(path,enforce_file_format=True)
        groups,_=scan_series((root/'dicom').glob('*'))
        v=load_series(next(iter(groups.values())))
        np.testing.assert_array_equal(v.data,self.hu*2+10)
    def test_multiframe_rejected(self):
        import copy
        entries=copy.deepcopy(self.entries);entries[0][1].NumberOfFrames=2
        with self.assertRaisesRegex(ValueError,'単一'):load_series(entries)

if __name__=='__main__':unittest.main()
