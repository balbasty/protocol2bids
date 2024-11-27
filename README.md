# protocol2bids


This little tool attempts to convert protocol printouts of various MRI
vendors to BIDS sidecars. However, this conversion mostly relies on guesswork,
and should therefore not be taken at face value. It might nonetheless be useful
when BIDSifying "old" public datasets for which only PDF protocols are available.

## Installation

```shell
pip install protocol2bids @ git+https://github.com/balbasty/protocol2bids
```

## Usage

```text
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃         protocol2bids : Convert protocol printouts to BIDS sidecars         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

╭─ Commands ──────────────────────────────────────────────────────────────────╮
│ --help,-h  Display this message and exit.                                   │
│ --version  Display application version.                                     │
╰─────────────────────────────────────────────────────────────────────────────╯
╭─ Parameters ────────────────────────────────────────────────────────────────╮
│ *  INP,--inp   Path to input protocol file [required]                       │
│ *  OUT,--out   Path to output JSON file [required]                          │
│    --hints     Protocol hints (ex: "siemens.vb")                            │
│    --nii       Path(s) to nifti file(s) (to read shape/affine from)         │
│    --defaults  Dictionary of default BIDS metadata                          │
│    --assigns   Dictionary of BIDS metadata to assign                        │
╰─────────────────────────────────────────────────────────────────────────────╯
```

```shell
>> protocol2bids /path/to/printout.pdf /path/to/sidecar.json
```

## List of JSON keys set (or not) by protocol2bids


Note that `protocol2bids` operates on a _"rather ignore than fail"_ basis.
Therefore, keys are only written when enough information is found in the
protocol. None of the keys listed belows are ensured to be written.

**Legend**:

* ⛔ `protocol2bids` never writes this key
* ✅ `protocol2bids` may write this key
* Ⓢ `protocol2bids` may write this key for SIEMENS protocols
* Ⓟ `protocol2bids` may write this key for PHILIPS protocols
* Ⓖ `protocol2bids` may write this key for GE protocols
* M mandatory/required by BIDS
* R recomended by BIDS
* O optional by BIDS

| Key                                | DICOM                      | Level        | Type                        | Unit   | Protocol2BIDS | Enum                                                             | Notes                            |
| ---------------------------------- | -------------------------- | ------------ | --------------------------- | ------ | ------------- | ---------------------------------------------------------------- | -------------------------------- |
| ▼ **BIDS**                         | <hr>                       | <hr>         | <hr>                        | <hr>   | <hr>          | <hr>                                                             | <hr>                             |
| Manufacturer                       | 0008,0070                  | R            | string                      |        | ✅            |                                                                  |                                  |
| ManufacturersModelName             | 0008,1090                  | R            | string                      |        | ✅            |                                                                  |                                  |
| DeviceSerialNumber                 | 0018,1000                  | R            | string                      |        | ⛔            |                                                                  |                                  |
| StationName                        | 0008,1010                  | R            | string                      |        | ⛔            |                                                                  |                                  |
| SoftwareVersions                   | 0018,1020                  | R            | string                      |        | Ⓢ            |                                                                  |                                  |
| MagneticFieldStrength              | 0018,0087                  | R            | number                      | T      | ✅            |                                                                  |                                  |
| ReceiveCoilName                    | 0018,1250                  | R            | string                      |        | ⛔            |                                                                  |                                  |
| ReceiveCoilActiveElements          |                            | R            | string                      |        | Ⓢ            |                                                                  |                                  |
| GradientSetType                    |                            | R            | string                      |        | ⛔            |                                                                  |                                  |
| MRTransmitCoilSequence             | 0018,9049                  | R            | string                      |        | ⛔            |                                                                  |                                  |
| MatrixCoilMode                     |                            | R            | string                      |        | Ⓢ            |                                                                  |                                  |
| CoilCombinationMethod              |                            | R            | string                      |        | Ⓢ            |                                                                  |                                  |
| NumberTransmitCoilActiveElements   |                            | O            | integer                     |        | ⛔            |                                                                  |                                  |
| TablePosition                      |                            | O            | array[number]               | mm     | ⛔            |                                                                  | R if `chunk-`                    |
| InstitutionName                    | 0008,0080                  | R            | string                      |        | ⛔            |                                                                  |                                  |
| InstitutionAddress                 | 0008,0081                  | R            | string                      |        | ⛔            |                                                                  |                                  |
| InstitutionalDepartmentName        | 0008,1040                  | R            | string                      |        | ⛔            |                                                                  |                                  |
| PulseSequenceType                  |                            | R            | string                      |        | ✅            |                                                                  |                                  |
| ScanningSequence                   | 0018,0020                  | R            | array[string]               |        | ✅            | {SR, GE, IR, EP}                                                 |                                  |
| SequenceVariant                    | 0018,0021                  | R            | array[string]               |        | ✅            | {SS, TRSS, MP, SK, MTC, SP, OSP}                                 |                                  |
| ScanOptions                        | 0018,0022                  | R            | array[string]               |        | ✅            | {PER, RG, CG, PPG, FC, PFF, PFP, SP, FS}                         |                                  |
| SequenceName                       | 0018,0024                  | R            | string                      |        | Ⓢ            |                                                                  |                                  |
| PulseSequenceDetails               |                            | R            | string                      |        | ⛔            |                                                                  |                                  |
| NonlinearGradientCorrection        |                            | R, M[+pet]   | boolean                     |        | ⛔            |                                                                  |                                  |
| MRAcquisitionType                  | 0018,0023                  | R, M[asl]    | string                      |        | ✅            | {2D, 3D}                                                         |                                  |
| MTState                            | 0018,9020                  | R            | boolean                     |        | ⛔            |                                                                  |                                  |
| MTOffsetFrequency                  |                            | O            | number                      | Hz     | ⛔            |                                                                  |                                  |
| MTPulseBandwidth                   |                            | O            | number                      | Hz     | ⛔            |                                                                  |                                  |
| MTNumberOfPulses                   |                            | O            | integer                     |        | ⛔            |                                                                  |                                  |
| MTPulseShape                       |                            | O            | string                      |        | ⛔            | {HARD, GAUSSIAN, GAUSSHANN, SINC, SINCHANN, SINCGAUSS, FERMI}    |                                  |
| MTPulseDuration                    |                            | O            | number                      | s      | ⛔            |                                                                  |                                  |
| SpoilingState                      |                            | R            | boolean                     |        | ✅            |                                                                  |                                  |
| SpoilingType                       |                            | O            | string                      |        | ✅            | {RF, GRADIENT, COMBINED}                                         |                                  |
| SpoilingRFPhaseIncrement           |                            | O            | number                      | deg    | ⛔            |                                                                  |                                  |
| SpoilingGradientMoment             |                            | O            | number                      | mT.s/m | ⛔            |                                                                  |                                  |
| SpoilingGradientDuration           |                            | O            | number                      | s      | ⛔            |                                                                  |                                  |
| WaterSuppression                   |                            | O            | boolean                     |        | ⛔            |                                                                  |                                  |
| WaterSuppressionTechnique          |                            | O            | string                      |        | ⛔            | {CHESS, VAPOR, ...}                                              |                                  |
| B0ShimmingTechnique                |                            | O            | string                      |        | ⛔            |                                                                  |                                  |
| B1ShimmingTechnique                |                            | O            | string                      |        | ⛔            |                                                                  |                                  |
| NumberShots                        |                            | R            | integer &vert; array[integer] |        | ⛔            |                                                                  |                                  |
| ParallelReductionFactorInPlane     | 0018,9069                  | R            | number                      |        | ✅            |                                                                  |                                  |
| ParallelReductionFactorOutOfPlane  | 0018,9155                  | R            | number                      |        | ✅            |                                                                  |                                  |
| ParallelAcquisitionTechnique       |                            | R            | string                      |        | ✅            | {GRAPPA, SENSE, ...}                                             |                                  |
| PartialFourier                     | 0018,9081                  | R            | number                      |        | ✅            |                                                                  |                                  |
| PartialFourierDirection            | 0018,9036                  | R            | string                      |        | ✅            | {PHASE, FREQUENCY, SLICE_SELECT, COMBINATION}                    |                                  |
| EffectiveEchoSpacing               |                            | R            | number                      | s      | ✅            |                                                                  | M if unwarp                      |
| MixingTime                         |                            | R            | number                      | s      | ⛔            |                                                                  |                                  |
| PhaseEncodingDirection             |                            | R            | string                      |        | ✅            | {i, i-, j, j-, k, k-}                                            |                                  |
| TotalReadoutTime                   |                            | R            | number                      | s      | ✅            |                                                                  | M if topup                       |
| EchoTime                           | 0018,0081                  | R            | number &vert; array[number]   | s      | ✅            |                                                                  | M if `asl`,  unwarp,  multi-echo |
| InversionTime                      | 0018,0082                  | R            | number                      | s      | ✅            |                                                                  |                                  |
| DwellTime                          | 0019,1018                  | R            | number                      | s      | Ⓢ            |                                                                  | M if unwarp3d                    |
| SliceTiming                        |                            | R            | number &vert; array[number]   | s      | ⛔            |                                                                  | M if `asl` + 2D                  |
| SliceEncodingDirection             |                            | R            | string                      |        | ✅            | {i, i-, j, j-, k, k-}                                            |                                  |
| FlipAngle                          | 0018,1314                  | R            | number                      | deg    | ✅            |                                                                  | M if looklocker                  |
| NegativeContrast                   |                            | O            | boolean                     |        | ⛔            |                                                                  |                                  |
| MultibandAccelerationFactor        |                            | R            | number                      |        | ✅            |                                                                  |                                  |
| RepetitionTimeExcitation           | 0018,0080                  | R            | number                      | s      | ✅            |                                                                  |                                  |
| RepetitionTimePreparation          |                            | R            | number                      | s      | ✅            |                                                                  |                                  |
| RepetitionTime                     | 0020,0110 &vert; 0018,0080 | M[func]      | number                      | s      | ✅            |                                                                  | -VolumeTiming                    |
| VolumeTiming                       |                            | M[func]      | array[number]               | s      | ⛔            |                                                                  | -RepetitionTime, DelayTiem       |
| TaskName                           |                            | M[func]      | string                      |        | ⛔            |                                                                  |                                  |
| NumberOfVolumesDiscardedByScanner  |                            | R[func]      | integer                     |        | ⛔            |                                                                  |                                  |
| NumberOfVolumesDiscardedByUser     |                            | R[func]      | integer                     |        | ⛔            |                                                                  |                                  |
| DelayTime                          |                            | R[func]      | number                      | s      | ⛔            |                                                                  | -VolumeTiming                    |
| AcquisitionDuration                | 0018,9073                  | R[func]      | number                      | s      | ⛔            |                                                                  | -RepetitionTime                  |
| DelayAfterTrigger                  |                            | R[func]      | number                      | s      | ⛔            |                                                                  |                                  |
| Instructions                       |                            | R[func]      | string                      |        | ⛔            |                                                                  |                                  |
| TaskDescription                    |                            | R[func]      | string                      |        | ⛔            |                                                                  |                                  |
| CogAtlasID                         |                            | R[func]      | string                      |        | ⛔            |                                                                  |                                  |
| CogPOID                            |                            | R[func]      | string                      |        | ⛔            |                                                                  |                                  |
| EchoTime1                          |                            | M[phasediff] | number                      | s      | ✅            |                                                                  |                                  |
| EchoTime2                          |                            | M[phasediff] | number                      | s      | ✅            |                                                                  |                                  |
| Units                              |                            | M[fmap]      | string                      |        | ✅            | {Hz, rad/s, T}                                                   |                                  |
| ▼ **dcm2niix**                     | <hr>                       | <hr>         | <hr>                        | <hr>   | <hr>          | <hr>                                                             | <hr>                             |
| Modality                           | 0008,0060                  |              | string                      |        | ✅            | {MR, CT, PT, ...}                                                |                                  |
| ConversionSoftware                 |                            |              | string                      |        | ⛔            |                                                                  |                                  |
| ConversionSoftwareVersion          |                            |              | string                      |        | ⛔            |                                                                  |                                  |
| BodyPartExamined                   | 0018,0015                  |              | string                      |        | ⛔            |                                                                  |                                  |
| PatientPosition                    | 0020,0032                  |              | string                      |        | ⛔            |                                                                  |                                  |
| ProcedureStepDescription           | 0040,0254                  |              | string                      |        | ⛔            |                                                                  |                                  |
| SeriesDescription                  | 0008,103E                  |              | stirng                      |        | ⛔            |                                                                  |                                  |
| ProtocolName                       | 0018,1030                  |              | string                      |        | ⛔            |                                                                  |                                  |
| ImageType                          | 0008,0008                  |              | string                      |        | ✅            |                                                                  |                                  |
| AcquisitionTime                    | 0008,0032                  |              | string                      |        | ⛔            |                                                                  | TODO                             |
| AcquisitionNumber                  | 0020,0012                  |              | integer                     |        | ⛔            |                                                                  |                                  |
| ImageComments                      | 0020,4000                  |              | string                      |        | ⛔            |                                                                  |                                  |
| AcquisitionMatrixPE                | 0018,9231                  |              | integer                     |        | ✅            |                                                                  |                                  |
| VendorReportedEchoSpacing          |                            |              | number                      | s      | Ⓢ            |                                                                  |                                  |
| DerivedVendorReportedEchoSpacing   |                            |              | number                      | s      | ⛔            |                                                                  |                                  |
| EchoNumber                         |                            |              | integer                     |        | ⛔            |                                                                  |                                  |
| EstimatedEffectiveEchoSpacing      |                            |              | number                      | s      | ⛔            |                                                                  |                                  |
| EstimatedTotalReadoutTime          |                            |              | number                      | s      | ⛔            |                                                                  |                                  |
| VariableFlipAngleFlag              | 0018,1315                  |              | boolean                     |        | ⛔            |                                                                  |                                  |
| ImageOrientationPatientDICOM       | 0020,0037                  |              | array[number]               |        | ⛔            |                                                                  |                                  |
| ImagingFrequency                   | 0018,0084 &vert; 0018,9098 |              | number                      | MHz    | Ⓢ            |                                                                  |                                  |
| InPlanePhaseEncodingDirectionDICOM | 0018,1312                  |              | string                      |        | ⛔            | {ROW, COL}                                                       |                                  |
| NumberOfAverages                   | 0018,0083                  |              | integer                     |        | Ⓢ            |                                                                  |                                  |
| PercentPhaseFOV                    | 0018,0094                  |              | number                      | pct    | Ⓢ            |                                                                  |                                  |
| PercentSampling                    | 0018,0093                  |              | number                      | pct    | ⛔            |                                                                  |                                  |
| FrequencyEncodingSteps             | 0018,9058                  |              | integer                     |        | ⛔            |                                                                  |                                  |
| PhaseEncodingSteps                 | 0018,0089 &vert; 0018,9231 |              | integer                     |        | ⛔            |                                                                  |                                  |
| PhaseEncodingStepsOutOfPlane       | 0018,9232                  |              | integer                     |        | ⛔            |                                                                  |                                  |
| PixelBandwidth                     | 0018,0095                  |              | number                      | Hz     | ✅            |                                                                  |                                  |
| RepetitionTimeInversion            |                            |              | number                      | s      | ✅            |                                                                  |                                  |
| SAR                                | 0018,1316 &vert; 0018,9181 |              | number                      | W/kg   | ⛔            |                                                                  |                                  |
| SliceThickness                     | 0018,0050                  |              | number                      | mm     | ✅            |                                                                  |                                  |
| SpacingBetweenSlices               | 0018,0088                  |              | numbe                       | mm     | ✅            |                                                                  |                                  |
| ▼ **DICOM (extra)**                | <hr>                       | <hr>         | <hr>                        | <hr>   | <hr>          | <hr>                                                             | <hr>                             |
| EchoPulseSequence                  | 0018,9008                  |              | string                      |        | ✅            | {SPIN, GRADIENT, BOTH}                                           |                                  |
| MultipleSpinEcho                   | 0018,9011                  |              | boolean                     |        | ✅            |                                                                  |                                  |
| MultiPlanarExcitation              | 0018,9012                  |              | boolean                     |        | ✅            |                                                                  |                                  |
| PhaseContrast                      | 0018,9014                  |              | boolean                     |        | ⛔            |                                                                  |                                  |
| VelocityEncodingDirection          | 0018,9090                  |              | array[number]               |        | ⛔            |                                                                  |                                  |
| TimeOfFlightContrast               | 0018,9015                  |              | boolean                     |        | ✅            |                                                                  |                                  |
| ArterialSpinLabelingContrast       | 0018,9250                  |              | string                      |        | ✅            | {CONTINUOUS, PSEUDOCONTINUOUS, PULSED}                           |                                  |
| SteadyStatePulseSequence           | 0018,9017                  |              | string                      |        | ✅            | {FREE_PRECESSION, TRANSVERSE, TIME_REVERSED, LONGITUDINAL, NONE} |                                  |
| EchoPlanarPulseSequence            | 0018,9018                  |              | boolean                     |        | ✅            |                                                                  |                                  |
| SaturationRecovery                 | 0018,9024                  |              | boolean                     |        | ⛔            |                                                                  |                                  |
| SpectrallySelectedSuppression      | 0018,9025                  |              | string                      |        | ⛔            | {FAT, WATER, FAT_AND_WATER, SILICON_GEL, NONE}                   |                                  |
| OversamplingPhase                  | 0018,9029                  |              | string                      |        | ✅            | {2D, 3D, 2D_3D, NONE}                                            |                                  |
| GeometryOfKSpaceTraversal          | 0018,9032                  |              | string                      |        | ✅            | {RECTILINEAR, RADIAL, SPIRAL}                                    |                                  |
| SegmentedKSpaceTraversal           | 0018,9033                  |              | string                      |        | ⛔            | {SINGLE, PARTIAL, FULL}                                          |                                  |
| RectilinearPhaseEncodeReordering   | 0018,9034                  |              | string                      |        | ✅            | {LINEAR, CENTRIC, SEGMENTED, REVERSE_LINEAR, REVERSE_CENTRIC}    |                                  |
| NumberOfKSpaceTrajectories         | 0018,9093                  |              | integer                     |        | ⛔            |                                                                  |                                  |
| CoverageOfKSpace                   | 0018,9094                  |              | string                      |        | ⛔            | {FULL, CYLINDRICAL, ELLIPSOIDAL, WEIGHTED}                       |                                  |
| EchoTrainLength                    | 0018,0091                  |              | integer                     |        | ✅            |                                                                  |                                  |
| ▼ **protocol2bids**                | <hr>                       | <hr>         | <hr>                        | <hr>   | <hr>          | <hr>                                                             | <hr>                             |
| SliceGap                           |                            |              | number                      | mm     | ✅            |                                                                  |                                  |
| VendorReportedRepetitionTime       |                            |              | number                      | s      | ✅            |                                                                  |                                  |
| DirectionFE                        |                            |              | string                      |        | ✅            | {LR, RL, PA, AP, SI, IS}                                         |                                  |
| DirectionPE                        |                            |              | string                      |        | ✅            | {LR, RL, PA, AP, SI, IS}                                         |                                  |
| DirectionSE                        |                            |              | string                      |        | ✅            | {LR, RL, PA, AP, SI, IS}                                         |                                  |
| HasPartialFourierFE                |                            |              | boolean                     |        | ✅            |                                                                  |                                  |
| HasPartialFourierPE                |                            |              | boolean                     |        | ✅            |                                                                  |                                  |
| HasPartialFourierSE                |                            |              | boolean                     |        | ✅            |                                                                  |                                  |
| AcquisitionMatrixFE                | 0018,9231                  |              | integer                     |        | ✅            |                                                                  |                                  |
| AcquisitionMatrixSE                |                            |              | integer                     |        | ✅            |                                                                  |                                  |
| OversampledAcquisitionMatrixFE     |                            |              | integer                     |        | ✅            |                                                                  |                                  |
| OversampledAcquisitionMatrixPE     |                            |              | integer                     |        | ✅            |                                                                  |                                  |
| OversampledAcquisitionMatrixSE     |                            |              | integer                     |        | ✅            |                                                                  |                                  |
| FieldOfViewFE                      |                            |              | number                      | mm     | ✅            |                                                                  |                                  |
| FieldOfViewPE                      |                            |              | number                      | mm     | ✅            |                                                                  |                                  |
| FieldOfViewSE                      |                            |              | number                      | mm     | ✅            |                                                                  |                                  |
