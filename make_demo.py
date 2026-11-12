"""Generate a synthetic phantom, never patient data or the exercise-5 result."""
from pathlib import Path
import numpy as np
import tifffile
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian, CTImageStorage

def generate(root):
    root=Path(root); (root/'dicom').mkdir(parents=True,exist_ok=True)
    z,y,x=np.mgrid[-1:1:48j,-1:1:80j,-1:1:96j]
    body=(x/.9)**2+(y/.78)**2 < 1
    lungs=(((x-.34)/.23)**2+(y/.50)**2+(z/.91)**2<1) | (((x+.34)/.23)**2+(y/.50)**2+(z/.91)**2<1)
    hu=np.full(z.shape,-1000,dtype=np.int16);hu[body]=35;hu[lungs]=-800
    hu[(x/.11)**2+((y-.5)/.12)**2<1]=800
    series,study,frame=generate_uid(),generate_uid(),generate_uid()
    for k in range(48):
        meta=FileMetaDataset();meta.TransferSyntaxUID=ExplicitVRLittleEndian
        meta.MediaStorageSOPClassUID=CTImageStorage;meta.MediaStorageSOPInstanceUID=generate_uid()
        ds=FileDataset('',{},file_meta=meta,preamble=b'\0'*128)
        ds.SOPClassUID=meta.MediaStorageSOPClassUID;ds.SOPInstanceUID=meta.MediaStorageSOPInstanceUID
        ds.StudyInstanceUID=study;ds.SeriesInstanceUID=series;ds.FrameOfReferenceUID=frame
        ds.PatientName='SYNTHETIC^DEMO';ds.PatientID='DEMO-NOT-PATIENT';ds.Modality='CT'
        ds.SeriesDescription='Synthetic phantom (not exercise 5)'
        ds.Rows=80;ds.Columns=96;ds.SamplesPerPixel=1;ds.PhotometricInterpretation='MONOCHROME2'
        ds.BitsAllocated=16;ds.BitsStored=16;ds.HighBit=15;ds.PixelRepresentation=1
        ds.PixelSpacing=[2,2];ds.SliceThickness=3;ds.ImageOrientationPatient=[1,0,0,0,1,0]
        ds.ImagePositionPatient=[0,0,k*3];ds.InstanceNumber=k+1
        ds.RescaleSlope=1;ds.RescaleIntercept=0;ds.WindowCenter=-600;ds.WindowWidth=1500
        ds.PixelData=hu[k].astype('<i2').tobytes()
        ds.save_as(root/'dicom'/f'slice_{k+1:03}.dcm',enforce_file_format=True)
    tifffile.imwrite(root/'synthetic_lung_mask.tif',lungs.astype('uint8')*255,photometric='minisblack',metadata={'axes':'ZYX'},compression=None)
    return hu, lungs

if __name__=='__main__':
    generate(Path(__file__).parent/'demo')
