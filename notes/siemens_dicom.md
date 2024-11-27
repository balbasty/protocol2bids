# SIEMENS protocols

## Acronyms

- `FE`: frequency-encoding
- `PE`: phase-encoding
- `SE`: slice-encoding

## Protocol options

### `Routine`
- `Routine/FoV read` (mm): Field of view along the FE direction
  (if there was no oversampling)
- `Routine/FoV phase` (%): Field of view along the PE direction,
  as a percentage of the FE FoV (if there was no oversampling)
- `Routine/Phase oversampling` (%): Oversampling along the PE direction.
  The real k-space acquisition matrix is
  `OversampledAcquisitionMatrixPE = ceil[(Routine/Phase oversampling) * (Resolution/Phase resolution) * (Resolution/Base resolution)]`
- `Routine/Slice oversampling` (%): Oversampling along the FE direction.
  The real k-space acquisition matrix is
  `OversampledAcquisitionMatrixSE = ceil[(Routine/Slice oversampling) * (Resolution/Slice resolution) * (Resolution/Base resolution)]`

In SIEMENS language:
- a **slice** is a "thin" slice-selected block of tissue (i.e.,
a slice-select graident is played such that only a z-portion is within
the excitation bandwidth). Used in 2D acquisitions.
- a **slab** is a "thick" slice that is further phase-encoded.
  Used in 3D acquisitions.

therefore we have:
- `Routine/Slice group 1/Slices` (int): Number of slices (2D)
- `Routine/Slab group 1/Slabs` (int): Number of slabs (3D)
- `Routine/Slices per slab` (uint): Number of slices in each slab (3D)
- `Routine/Slice group 1/Dist. factor` (%): Slice gap, as a percentage of slice thickness
- `Routine/Slice thickness` (mm): Slice thickness.
    * If 3D acquisition (slab), the FoV along SE is
      `(Routine/Slab group 1/Slabs) * (Routine/Slices per slab) * (Routine/Slice thickness)`
    * If 2D acquisition (slice), the FoV along SE is
      `(Routine/Slice group 1/Slices) * Routine/Slice thickness) * (1 + (Routine/Slice group 1/Dist. factor))`

### `Resolution`
- `Resolution/Base resolution` (uint): acquisition matrix along the FE direction,
  per `Routine/FoV read` "unit".
  (if there was no oversampling or partial fourier == asymmetric echo)
- `Resolution/Phase resolution` (%): acquisition matrix along the PE direction,
  per `Routine/FoV read` "unit", as a percentage of the FE resolution
  (if there was no oversampling, partial fourier or in-plane acceleration)
  !! Note that this means that the acquisition matrix along the PE direction is
  `(Resolution/Base resolution) * (Resolution/Phase resolution) * (Routine/FoV phase)`
  (if there was no oversampling)!!
- `Resolution/Slice resolution` (%): acquisition matrix along the SE direction,
  when it is a second phase-encoding direction (3D acq),
  as a percentage of the FE resolution
  (if there was no oversampling, partial fourier or through-plane acceleration)
- `Resolution/Phase partial Fourier` ('Off' or %): Partial fourier along the PE direction
- `Resolution/Slice partial Fourier` ('Off' or %): Partial fourier along the SE direction (3D acq)
- `Resolution/Interpolation` (???): When the reconstruction matrix differs from the acqusition matrix
- `Resolution/Accel. factor PE` (int): acceleration factor in-plane (along PE)
- `Resolution/Accel. factor 3D` (int): acceleration factor through-plane (along SE)
- `Resolution/Ref. lines PE` (int): number of reference lines (along PE) to
  estimate the GRAPPA kernel.

### `Sequence`
- `Sequence/Bandwidth` (Hz/px):
    * EPI: bandwidth per pixel along the PE direction
    * Otherwise: bandwidth per pixel along the FE direction
- `Sequence/Echo spacing` (ms): Time between successive echos
    * EPI: time between two echoes within an echo-train along PE
    * TFL: time between successive echoes along PE == Excitation TR
- `Sequence/EPI factor` (int): Echo train length (EPI)
- `Sequence/Turbo factor` (int): Echo train length (TSE)
    * What does it mean in TFL sequence?

## dcm2niix

- `PartialFourier = ASC[sKSpace.ucPhasePartialFourier]` (%):
  Proportion of k-space acquired `
- `Interpolation2D = ASC[sKSpace.uc2DInterpolation]` (bool):
  Whether k-space zero-filling was used
- `BaseResolution = ASC[sKSpace.lBaseResolution]` (uint):
  Acquisition matrix along the FE direction
- `PhaseResolution = ASC[sKSpace.dPhaseResolution]` (%):
  Acquisition matrix along the PE direction,
  as a percentage of the FE resolution
- `PhaseOversampling = ASC[sKSpace.dPhaseOversamplingForDialog]` (%):
  Oversampling along the PE direction
- `PercentPhaseFOV = DCM[PercentPhaseFOV (0018,0094)]` (%)
- `EchoTrainLength = DCM[EchoTrainLength (0018,0091)]` (uint):
  `≈ PhaseEncodingSteps/ParallelReductionFactorInPlane` (if EPI)
- `PhaseEncodingSteps = DCM[PhaseEncodingSteps (0018,0089)]` (uint):
  `≈ AcquisitionMatrixPE * PartialFourier * (1 + PhaseOversampling)`
  [i.e., it is NOT reduced by PAT]
- `AcquisitionMatrixPE = DCM[AcquisitionMatrixPE (0018,1310)]` (uint)
- `ReconMatrixPE = img.shape[AxisPE]` (int)
- `BandwidthPerPixelPhaseEncode = DCM[BandwidthPerPixelPhaseEncode (0019, 1028)]`
- `EffectiveEchoSpacing := 1/[BandwidthPerPixelPhaseEncode * ReconMatrixPE]` (Hz/px)
- `ParallelReductionFactorInPlane = DCM[ParallelReductionFactorInPlane (0051,1011)] = ASC[sPat.lAccelFactPE]` (int)
- `DerivedVendorReportedEchoSpacing` (ms)
- `VendorReportedEchoSpacing = ASC[sFastImaging.lEchoSpacing]` (ms)
- `TotalReadoutTime := EffectiveEchoSpacing * (ReconMatrixPE - 1)` (ms):
  [i.e., for all practical purposes, is basically just `1/BandwidthPerPixelPhaseEncode`]

## protocol2bids

```
AcquisitionMatrixFE                 = (Resolution/Base resolution)
AcquisitionMatrixPE                 = round[
                                        (Routine/FoV phase) *
                                        (Resolution/Phase resolution) *
                                        (Resolution/Base resolution)
                                    ]
AcquisitionMatrixSE           (2D)  = (Routine/Slice group 1/Slices)
                              (3D)  = (Routine/Slab group 1/Slabs) * (Routine/Slices per slab)
OversampledAcquisitionMatrixFE      = 2 * (Resolution/Base resolution)  # FIXME: always the case?
OversampledAcquisitionMatrixPE      = round[
                                        (1 + Routine/Phase oversampling) *
                                        (Routine/FoV phase) *
                                        (Resolution/Phase resolution) *
                                        (Resolution/Base resolution)
                                    ]
OversampledAcquisitionMatrixSE      = round[
                                        (1 + Routine/Slice oversampling) *
                                        (Resolution/Slice resolution) *
                                        (Resolution/Base resolution)
                                    ]
ReconMatrixFE                       = (Resolution/Base resolution)
HasPartialFourierFE                 = (Sequence/Asymmetric echo != "Off")
HasPartialFourierPE                 = (Resolution/Phase partial Fourier != "Off")
HasPartialFourierSE                 = (Resolution/Slice partial Fourier != "Off")
PartialFourierPE                    = (Resolution/Phase partial Fourier)
PartialFourierSE                    = (Resolution/Slice partial Fourier)
FieldOfViewFE                       = (Routine/FoV read)
FieldOfViewPE                       = (Routine/FoV phase) * (Routine/FoV read)
FieldOfViewSE                 (2D)  = (Routine/Slice group 1/Slices) * Routine/Slice thickness) * (1 + (Routine/Slice group 1/Dist. factor))
                              (3D)  = (Routine/Slab group 1/Slabs) * (Routine/Slices per slab) * (Routine/Slice thickness)
ParallelReductionFactorInPlane      = (Resolution/Accel. factor PE)
ParallelReductionFactorOutOfPlane   = (Resolution/Accel. factor 3D)
EchoTrainLength               (EPI) = (Sequence/EPI factor)
                              (TSE) = (Sequence/Turbo factor)
AcquiredPE                          = [AcquisitionMatrixPE] * [PartialFourierPE] / [ParallelReductionFactorInPlane]
AcquiredSE                          = [AcquisitionMatrixSE] * [PartialFourierSE] / [ParallelReductionFactorOutOfPlane]
OversampledAcquiredPE               = [OversampledAcquisitionMatrixPE] * [PartialFourierPE] / [ParallelReductionFactorInPlane]
OversampledAcquiredSE               = [OversampledAcquisitionMatrixSE] * [PartialFourierSE] / [ParallelReductionFactorOutOfPlane]

# This is a Dicom field set by Siemens - does not account for parallel imaging
PhaseEncodingSteps                  = [OversampledAcquisitionMatrixPE] * [PartialFourierPE]

# FE bandwidth and related metrics are in reference to AcquisitionMatrixFE
# (not to OversampledAcquisitionMatrixFE)
PixelBandwidth                      = (Sequence/Bandwidth)
TotalSamplingTime                   = 1/(Sequence/Bandwidth)
DwellTime                           = 1/((Sequence/Bandwidth) * (Resolution/Base resolution))

# PE bandwidth and related metrics are in reference to AcquisitionMatrixPE
# (not to OversampledAcquisitionMatrixPE)
BandwidthPerPixelPhaseEncode  (EPI) = 1/((Sequence/Echo spacing)*([ReconMatrixPE]/(Resolution/Accel. factor PE))*(1 + Routine/Phase oversampling))
EchoSpacing                   (EPI) = (Sequence/Echo spacing)
EffectiveEchoSpacing          (EPI) = 1/([BandwidthPerPixelPhaseEncode] * [ReconMatrixPE])
                              (EPI) = (Sequence/Echo spacing) * (1 + Routine/Phase oversampling) / (Resolution/Accel. factor PE)
TotalReadoutTime              (EPI) = [EffectiveEchoSpacing] * ([ReconMatrixPE] - 1)
ActualReadoutTime             (EPI) = (Sequence/Echo spacing) * [OversampledAcquiredPE]
```

# Pulses

```
* Low SAR (3.84 ms)
    - Longer RF pulse with good slice profile
    - Reduced SAR values (lower amplitude)
    - Less crosstalk between slice; narrower gaps tolerated
    - Longer minimum TEs and TRs
* Normal (2.56 ms)
    - Normal RF pulse with good slice profile
    - Optimized SAR behavior
* Fast (1.28 ms)
    - Shorter RF pulse, with a compromised slice profile
    - Higher SAR compared to the other modes (higher amplitude)
    - Shorter echo spacing (ES)
    - Opportunity for shorter TEs and TRs
    - Fewer susceptibility artifacts
```
