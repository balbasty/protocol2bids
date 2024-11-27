# Vendor Sequence Dictionary

## Conversion

This table shows how various MRI sequences and options are named across vendors.

It is mostly derived from the "MRI Acronyms" leaflet edited by SIEMENS:

* [2010](https://www.mrgschedule.com/schedule_static/MRI_Acronyms.pdf)
* [2015](https://cdn0.scrvt.com/39b415fb07de4d9656c7b516d8e2d907/1800000000016934/2ade5adbaa62/MRI_Acronyms_1800000000016934.pdf)
* [2018](https://www.dkfz.de/en/radiologie/images/MR-Akronymliste.pdf)


| Description                                 | Siemens                                | GE                       | Philips                 | Hitachi                    | Toshiba / Canon            |
| ------------------------------------------- | -------------------------------------- | ------------------------ | ----------------------- | -------------------------- | -------------------------- |
| Spin Echo                                   | SE                                     | SE                       | SE                      | SE                         | SE                         |
| Gradient Echo                               | GRE                                    | GRE                      | FFE                     | GE                         | FE                         |
| Spoiled Gradient Echo                       | FLASH                                  | SPGR                     | T1-FFE                  | RS SARGE, RSSG             | FastFE                     |
| Coherent Gradient Echo                      | FISP                                   | GRASS                    | FFE                     | Rephased SARGE             | SSFP                       |
| Steady-State Free Precession                | PSIF                                   | SSFP                     | T2-FFE                  | Time-Reversed SARGE        | -                          |
| Balanced Steady-State Free Precession       | TrueFISP                               | FIESTA                   | Balanced FFE            | Balanced SARGE, BASG       | True SSFP                  |
| bSSFP Dual Excitation                       | CISS                                   | FIESTA                   | -                       | Phase Balanced SARGE, PBSG | -                          |
| Double Echo Steady State                    | DESS                                   | -                        | -                       | -                          | -                          |
| Multi-Echo Data Image Combination           | MEDIC                                  | MERGE                    | M-FFE                   | -                          | -                          |
| Ultrafast Gradient Echo                     | TurboFLASH                             | Fast GRE, Fast SPGR      | TFE                     | RGE                        | -                          |
| Ultrafast Gradient Echo 3D                  | MPRAGE                                 | 3D FGRE, 3D Fast SPGR    | 3D TFE                  | MPRAGE                     | 3D FFE                     |
| Volume Interpolated GRE                     | VIBE                                   | LAVA-XV                  | THRIVE                  | TIGRE                      | -                          |
| Body Diffusion                              | REVEAL                                 | -                        | DWIBS                   | -                          | Body Vision                |
| Susceptibility-Weighted Imaging             | SWI                                    | SWAN                     | (Venous BOLD)           | -                          | -                          |
| Dynamic MRA with k-space Manipulation       | TWIST                                  | TRICKS-XV                | Keyhole (4D-TRAK)       | -                          |                            |
| High-Resolution Bilateral Breast Imaging    | VIEWS                                  | VIBRANT-XV               | BLISS                   | -                          | RADIANCE                   |
| Non-contrast MR Angio, TSE-based            | NATIVE-SPACE                           | -                        | TRANCE                  | VASC FSE                   | FBI, CIA                   |
| Non-contrast MR Angio, TrueFISP-based       | NATIVE-TrueFISP                        | Inhance Inflow IR        | B-TRANCE                | VASC ASL                   | Time-SLIP                  |
| Parametric Mapping                          | MapIT                                  | CartiGram                | -                       | -                          |                            |
| **Inversion Recovery**                      | IR, TIR                                | IR, MPIR, FastIR         | IR-TSE                  | IR                         | IR                         |
| Short Tau IR                                | STIR                                   | STIR                     | STIR                    | STIR                       | FastSTIR                   |
| Long Tau IR                                 | Turbo Dark Fluid                       | FLAIR                    | FLAIR                   | FLAIR                      | FastFLAIR                  |
| True IR                                     | True IR                                | -                        | Real IR                 | -                          | FastIR                     |
| **Turbo Spin Echo/Fast Spin Echo**          | TSE                                    | FSE                      | TSE                     | FSE                        | FSE                        |
| Single-Shot TSE/FSE                         | HASTE                                  | Single-Shot FSE          | Single-Shot TSE         | Single-Shot FSE            | FASE                       |
| FSE/TSE with 90° Flip-Back Pulse            | RESTORE                                | FRFSE                    | DRIVE                   | Driven Equillibrium FSE    | T2 Puls FSE                |
| Hyper Echoes                                | Hyperecho                              | -                        | -                       | -                          | -                          |
| 3D TSE with Variable Flip Angle             | SPACE                                  | CUBE                     | VISTA                   | isoFSE                     | -                          |
| Number of Echoes                            | Turbo Factor                           | ETL                      | Turbo Factor            | Shot Factor                | ETL                        |
| Time Between Echoes                         | Echo Spacing                           | Echo Spacing             | Echo Spacing            | ITE                        | Echo Spacing               |
| **Echo Planar Imaging (EPI)**               | EPI                                    | EPI                      | EPI                     | EPI                        | EPI                        |
| Number of Echoes                            | EPI Factor                             | ETL                      | EPI Factor              | Shot Factor                | ETL                        |
| Diffusion-Weighted Imaging                  | DWI                                    | DWI                      | DWI                     | DWI                        | DWI                        |
| Apparent Diffusion Coefficient Map          | ADC                                    | ADC                      | ADC                     | ADC                        | ADC                        |
| Diffusion Tensor Imaging                    | DTI                                    | DTI                      | DTI                     | -                          | DTI                        |
| DTI Tractography (Fiber Tracking)           | DTI Tractography                       | FiberTrak                | FiberTrak               | -                          | -                          |
| **Turbo Gradient Spin Echo (GRASE)**        | TGSE                                   | -                        | GRASE                   | -                          | Hybrid EPI                 |
| **Motion Correction**                       |                                        |                          |                         |                            |                            |
| 1D Navigators for Cardiac Imaging           | 1D PACE                                | Navigators               | Navigators              | -                          | -                          |
| 2D Navigators for Abdominal Imaging         | 2D PACE                                | -                        | -                       | -                          | -                          |
| 3D Prospective Motion Correction for fMRI   | 3D PACE                                | -                        | -                       | -                          | -                          |
| 3D Retrospective Motion Correction for fMRI | 3D ART                                 | -                        | -                       | -                          | -                          |
| Motion Correction with Radial Blades        | BLADE                                  | PROPELLER                | MultiVane               | RADAR                      | JET                        |
| Soft Tissue Motion Correction               | BRACE                                  | -                        | -                       | -                          | -                          |
| **Parallel Acquisition Techniques**         | iPAT                                   |                          |                         |                            |                            |
| PAT: Image-based Algorithm                  | mSENSE                                 | ASSET                    | SENSE                   | RAPID                      | SPEEDER                    |
| PAT: k-space-based Algorithm                | GRAPPA                                 | ARC                      | -                       | -                          | -                          |
| Integrated Calibration                      | Auto-Calibration                       | Self-Calibration         | -                       | -                          | -                          |
| Separate Calibration                        | Turbo-Calibration                      |                          | CLEAR                   |                            |                            |
| **Sequence Parameters**                     |                                        |                          |                         |                            |                            |
| Repetition Time, Echo Time (in msec)        | TR, TE                                 | TR, TE                   | TR, TE                  | TR, TE                     | TR, TE                     |
| Inversion Time (in msec)                    | TI                                     | TI                       | TI                      | TI                         | TI                         |
| Averages                                    | Averages                               | NEX                      | NSA                     | NSA                        | NSA                        |
| Simultaneous Excitation                     | Simultaneous Excitation                | POMP                     | Multi-Slice             | Dual Slice                 | QuadScan                   |
| RF Pulse in Gradient Echo                   | Flip Angle                             | Flip Angle               | Flip Angle              | Flip Angle                 | Flip Angle                 |
| Scan Measurement Time                       | Acquisition Time, TA                   | Acquisition Time         | Acquisition Time        | Scan Time                  | Acquisition Time           |
| Distance Between Slices                     | Distance Factor (% of slice thickness) | Gap                      | Gap                     | Slice Interval             | Gap                        |
| Slice Interval                              | Off-center Shift                       | Off-center FoV           | Off-center FoV          | Off-center FoV             | Phase & Frequency Shift    |
| Field of View (FoV)                         | FoV [mm]                               | FoV [cm]                 | FoV [mm]                | FoV                        | FoV                        |
| Rectangular FoV                             | FoV Phase/Rectangular FoV              | Partial FoV (PFoV)       | Rectangular FoV         | Rectangular FoV            | Rectangular FoV            |
| Bandwidth                                   | Bandwidth [Hz/Px]                      | Receive Bandwidth [kHz]  | Fat/Water Shift [pixel] | Bandwidth                  | Bandwidth                  |
| Variable Bandwidth                          | Optimized bandwidth                    | Variable Bandwidth       | Optimized Bandwidth     | Variable Bandwidth         | Matched Bandwidth          |
| Frequency Oversampling                      | Oversampling                           | Anti-Aliasing            | Frequency Oversampling  | Frequency Oversampling     | Frequency Wrap Suppression |
| Phase Oversampling                          | Phase Oversampling                     | No Phase Wrap            | Fold-over Suppression   | Anti-Wrap                  | Phase Wrap Suppression     |
| Segmented k-Space                           | Lines/Segments                         | Views per segment        | Views/Segment           |                            | Segments                   |
| Time Delay/Block k-space                    | Time Delay                             | Intersegment Delay       | TD                      |                            | TD                         |
| Half Fourier Imaging                        | Half Fourier                           | 1/2 NEX; fractional NEX  | Half Scan               | Half Scan                  | AFI                        |
| Partial Echo                                | Asymmetric Echo                        | Partial Echo             | Partial Echo            | Half Echo                  | Matched Bandwidth          |
| Gradient Moment Nulling                     | GMR/Flow Comp                          | Flow Comp                | Flow Comp; Flag         | GR                         | FC                         |
| Ramped RF Pulse                             | TONE                                   | Ramped Pulse             | TONE                    | SSP                        | ISCE                       |
| Magnetization Transfer Contrast             | MTC, MTS                               | MTC                      | MTC                     | MTC                        | SORS-STC                   |
| Prep Pulse – Chemically                     | Fat Sat                                | Fat Sat/Chem Sat         | SPIR                    | Fat Sat                    | MSOFT                      |
| Water Excitation                            | Water Excitation                       | -                        | Proset                  | Water Excitation           | PASTA                      |
| Fat-Water separation                        | DIXON                                  | IDEAL                    | -                       | FatSep                     |                            |
| Prep Pulse - Spatially                      | Presat                                 | SAT                      | REST                    | PreSat                     | PreSat                     |
| Moving Sat Pulse                            | Travel Sat; Tracking Sat               | Walking Sat              | Travel REST             | Sequential Pre Sat         | BFAST                      |
| Scan Synchronization with ECG               | ECG Triggered                          | Cardiac Gated/Triggering | ECG Triggered/VCG       | ECG Triggered              | Cardiac Gated              |
| Delay after R-Wave                          | Trigger Delay; TD                      | Trigger Delay; TD        | Trigger Delay; TD       | Delay Time                 | Trigger Delay; TD          |
| Respiratory Gating                          | Respiratory Gated                      | Respiratory Comp         | Trigger; PEAR           | MAR                        | Respiratory Gated          |
| Multi-Channel RF Coil Sensitivity Norm.     | Prescan Normalize                      | PURE                     | CLEAR                   | NATURAL                    |                            |
| Central k-space Filling Arterial Vis.       | Elliptical Scanning                    | Elliptic Centric         | CENTRA                  | PEAKS                      | DRKS                       |

## Acronyms

### Dicom

This table lists acronyms used in the DICOM standard.

| Acronym          | Meaning                                                                          |
| ---------------- | -------------------------------------------------------------------------------- |
|                  | **Sequences**                                                                    |
| SE               | Spin Echo                                                                        |
| GR               | Gradient Recalled                                                                |
| IR               | Inversion Recovery                                                               |
| EP               | Echo Planar                                                                      |
|                  | **Variants**                                                                     |
| SS               | Steady State                                                                     |
| TRSS             | Time Reversed Steady State                                                       |
| MP               | Magnetization Prepared                                                           |
| SK               | Segmented K space                                                                |
| MTC              | Magnetization Transfer Contrast                                                  |
| SP               | SPoiled                                                                          |
| OSP              | OverSampling Phase                                                               |
|                  | **Options**                                                                      |
| PER              | Phase Encode Reordering                                                          |
| RG               | Respiratory Gating                                                               |
| CG               | Cardiac Gating                                                                   |
| PPG              | Peripheral Pulse Gating                                                          |
| FC               | Flow Compensation                                                                |
| PFF              | Partial Fourier - Frequency                                                      |
| PFP              | Partial Fourier - Phase                                                          |
| SP               | Spatial Presaturation                                                            |
| FS               | Fat Saturation                                                                   |
|                  | **MR-Specific Image Type**                                                       |
| ANGIO_TIME       | Angio time acquisition (peripheral vascular/carotid)                             |
| ASL              | Arterial Spin Labeling                                                           |
| CINE             | Cardiac CINE                                                                     |
| DIFFUSION        | Collected to show diffusion effects                                              |
| DIXON            | Dixon Water Fat Imaging Techniques                                               |
| FLOW_ENCODED     | Flow Encoded                                                                     |
| FLUID_ATTENUATED | Fluid Attenuated T2 weighted                                                     |
| FMRI             | Collected for functional imaging calculations                                    |
| MAX_IP           | Maximum Intensity Projection                                                     |
| MIN_IP           | Minimum Intensity Projection                                                     |
| M_MODE           | Image line over time                                                             |
| METABOLITE_MAP   | Metabolite Maps from spectroscopy data                                           |
| MULTIECHO        | Multiple echoes with different contrast weighting                                |
| PROTON_DENSITY   | Proton density weighted                                                          |
| REALTIME         | Real-time collection of single slices                                            |
| STIR             | Short Tau Inversion Recovery                                                     |
| TAGGING          | Images with superposition of thin saturation bands                               |
| TEMPERATURE      | Images record temperature                                                        |
| T1               | T1 weighted                                                                      |
| T2               | T2 weighted                                                                      |
| T2_STAR          | T2* weighted                                                                     |
| TOF              | Time Of Flight weighted                                                          |
| VELOCITY         | Velocity encoded                                                                 |
| ANGIO            | Collected for the purpose of angiography                                         |
| CARDIAC          | Images of the heart                                                              |
| CARDIAC_GATED    | Cardiac gated images, other than of the heart                                    |
| CARDRESP_GATED   | Cardiac and respiratory gated images                                             |
| DYNAMIC          | An image in which the same anatomical volume is imaged at multiple times         |
| FLUOROSCOPY      | Real-time collection of single slices (e.g., CT or MR Fluoroscopy)               |
| LOCALIZER        | Collected for the purpose of planning other images                               |
| MOTION           | Collected for looking at body motion                                             |
| PERFUSION        | Collected for the purposes of perfusion calculations                             |
| PRE_CONTRAST     | Collected before contrast was administered                                       |
| POST_CONTRAST    | Collected during or after contrast was administered                              |
| RESP_GATED       | Respiratory gated images                                                         |
| REST             | Cardiac rest image set                                                           |
| STATIC           | A group of frames at varying spatial locations acquired at the same time         |
| STRESS           | Cardiac stress image set                                                         |
| VOLUME           | Set of frames that define a regularly sampled volume                             |
| NON_PARALLEL     | Set of frames that are not parallel                                              |
| PARALLEL         | Set of frames that are parallel but do not constitute a regularly sampled volume |
| WHOLE_BODY       | A group of frames of the whole body; the frames may be acquired at various times |

### Vendors

This table lists all possible acronyms (sequence or options) found in the MRI field.

The conversion to DICOM is mine, most;y obtained from guesswork.
It is absolutely not ensured that the DICOM file obtained from a given sequence
contains these exact DICOM tags.

| Acronym           | Meaning                                                                                        | DICOM        | Vendors                   |
| ----------------- | ---------------------------------------------------------------------------------------------- | ------------ | ------------------------- |
|                   | **Sequence acronyms**                                                                          |              |                           |
| SE                | Spin Echo                                                                                      | SE           | All                       |
| GRE               | Gradient Recalled Echo                                                                         | GR           | Siemens, GE               |
| GE                | Gradient Echo                                                                                  | GR           | Hitachi                   |
| FE                | Field Echo                                                                                     | GR           | Toshiba                   |
| FFE               | Fast Field Echo                                                                                | GR           | Philips, Toshiba          |
| SPGR              | SPoiled Gradient Recalled                                                                      | GR+SP        | GE                        |
| FLASH             | Fast Low Angle SHot                                                                            | GR+SP        | Siemens                   |
| T1-FFE            | T1 Fast Field Echo                                                                             | GR+SP        | Philips                   |
| SARGE, SG         | Steady state Acquisition Rewound Gradient Echo                                                 | GR           | Hitachi                   |
| RS-SARGE, RSSG    | RF Spoiled Steady State Acquisition Rewound Gradient Echo                                      | GR+SP        | Hitachi                   |
| FISP              | Fast Imaging with Steady state Precession                                                      | GR+SS        | Siemens                   |
| GRASS             | Gradient Recalled Acquisition in the Stead State                                               | GR+SS        | GE                        |
| R-SARGE           | Rephased Steady state Acquisition Rewound Gradient Echo                                        | GR+SS        | Hitachi                   |
| SSFP              | Steady State Free Precession                                                                   | GR+SS        | Toshiba                   |
| SSFP              | Steady State Free Precession                                                                   | GR+TRSS      | GE                        |
| PSIF              | Reversed FISP                                                                                  | GR+TRSS      | Siemens                   |
| T2-FFE            | T2 Fast Field Echo                                                                             | GR+TRSS      | Philips                   |
| TR-SARGE          | Time-Reversed Steady state Acquisition Rewound Gradient Echo                                   | GR+TRSS      | Hitachi                   |
| TrueFISP          | True Fast Imaging with Steady state Precession                                                 | GR+SS(b)     | Siemens                   |
| FIESTA            | Fast Imaging Employing Steady-state Acquisition                                                | GR+SS(b)     | GE                        |
| bFFE              | Balanced Fast Field Echo                                                                       | GR+SS(b)     | Philips                   |
| B-SARGE, BASG     | Balanced Steady state Acquisition Rewound Gradient Echo                                        | GR+SS(b)     | Hitachi                   |
| TrueSSFP          | True Steady State Free Precession                                                              | GR+SS(b)     | Toshiba                   |
| CISS              | Constructive Interference in Steady State                                                      |              | Siemens                   |
| PB-SARGE, PBSG    | Phase Balanced Steady state Acquisition Rewound Gradient Echo                                  |              | Hitachi                   |
| DESS              | Double Echo Steady State                                                                       |              | Siemens                   |
| MEDIC             | Multi-Echo Data Image Combination                                                              | GR+ME        | Siemens                   |
| MERGE             | Multiple Echo Recombined Gradient Echo                                                         | GR+ME        | GE                        |
| M-FFE             | Multi-echo Fast Field Echo                                                                     | GR+ME        | Philips                   |
| TurboFLASH        | Turbo Fast Low Angle SHot                                                                      | GR+SP+IR     | Siemens                   |
| FGRE, FSPGR       | Fast SPoiled Gradient Recalled                                                                 | GR+SP+IR     | GE                        |
| TFE               | Turbo Field Echo                                                                               | GR+SP+IR     | Philips                   |
| RGE               | Rapid Gradient Echo                                                                            | GR+SP+IR     | Hitachi                   |
| MPRAGE            | Magnetization-Prepared RApid Gradient Echo                                                     | GR+SP+IR+3D  | Siemens, Hitachi          |
| 3D FGRE, 3D FSPGR | 3D Fast SPoiled Gradient Recalled                                                              | GR+SP+IR+3D  | Siemens, Hitachi          |
| 3D TFE            | 3D Turbo Field Echo                                                                            | GR+SP+IR+3D  | Philips                   |
| 3D FFE            | 3D Fast Field Echo                                                                             | GR+SP+IR+3D  | Toshiba                   |
| VIBE              | Volumetric Interpolated Breath-hold Examination                                                | GR+SP+3D+ZF  | Siemens                   |
| LAVA-XV           | Liver Acceleration Volume Acquisition                                                          | GR+SP+3D+ZF  | GE                        |
| THRIVE            | T1-weighted High-Resolution Isotropic Volume Examination                                       | GR+SP+3D+ZF  | Philips                   |
| TIGRE             | T1-weighted GRadient Echo                                                                      | GR+SP+3D+ZF  | Hitachi                   |
| REVEAL            |                                                                                                | SE+EP+DW+PMC | Siemens                   |
| DWIBS             | Diffusion-weighted Whole-body Imaging with Background body signal Suppression                  | SE+EP+DW+FS  | Philips                   |
| SWI               | Susceptibility-Weighted Imaging                                                                | GR+SP+FC     | Siemens                   |
| SWAN              | Susceptibility-Weighted ANgiography                                                            | GR+SP+MR     | Philips                   |
| TWIST             | Time-resolved angiography With Interleaved Stochastic Trajectories                             |              | Siemens                   |
| TRICKS            | Time Resolved Imaging of Contrast KineticS                                                     |              | GE                        |
| VIEWS             |                                                                                                |              | Siemens                   |
| VIBRANT           | Volume Image Breast Assessment                                                                 |              | GE                        |
| BLISS             | BiLateral breast Imaging in the sagittal view with SeNSe                                       |              | Philips                   |
| RADIANCE          |                                                                                                |              | Toshiba                   |
| NATIVE            | Non-contrast MRA of ArTerIes and VEins                                                         |              | Siemens                   |
| TRANCE            | Triggered Angiography Non-Contrast-Enhanced                                                    |              | Philips                   |
| FBI               | Fresh Blood Imaging                                                                            |              | Toshiba                   |
| CIA               | Contrast-free Improved Angiography                                                             |              | Toshiba                   |
| Time-SLIP         | Time-Spatial Labeling Inversion Pulse                                                          |              | Toshiba                   |
| IR                | Inversion Recovery                                                                             |              | All                       |
| TIR               | Turbo Inversion Recovery                                                                       |              | Siemens                   |
| MPIR              | Magnetization-Prepared Inversion Recovery                                                      |              | GE                        |
| FIR               | Fast Inversion-Recovery                                                                        |              | GE                        |
| IR-TSE            | Inversion-Recovery Turbo Spin Echo                                                             |              | Philips                   |
| STIR              | Short Tau Inversion Recovery                                                                   |              | All                       |
| FLAIR             | FLuid Attenuated Inversion Recovery                                                            |              | All                       |
| Turbo Dark Fluid  |                                                                                                |              | Siemens                   |
| TrueIR            | True Inversion Recovery                                                                        |              | Siemens                   |
| RealIR            | Real Inversion Recovery                                                                        |              | Philips                   |
| FastIR            | Fast Inversion Recovery                                                                        |              | Toshiba                   |
| TSE               | Turbo Spin Echo                                                                                | SE+SK        | Siemens, Philips          |
| FSE               | Fast Spin Echo                                                                                 | SE+SK        | GE, Hitachi, Toshiba      |
| HASTE             | Half-Fourier Acquisition Single-shot Turbo spin Echo                                           | SE+PF        | Siemens                   |
| SS-FSE            | Single Shot Fast Spin Echo                                                                     | SE+PF        | GE, Hitachi               |
| SSH-TSE           | Single SHot Turbo Spin Echo                                                                    | SE+PF        | Philips                   |
| UFSE              | Ultra Fast Spin Echo                                                                           | SE+PF        | Philips                   |
| FASE              | Fast Advanced Spin Echo                                                                        | SE+PF        | Toshiba                   |
| RESTORE           |                                                                                                |              | Siemens                   |
| FRFSE             | Fast Recovery Fast Spin Echo                                                                   |              | GE                        |
| DRIVE             | DRIVen Equilibrium                                                                             |              | Philips                   |
| DE-FSE            | Driven Equilibrium Fast Spin Echo                                                              |              | Hitachi                   |
| DEFT              | Driven Equilibrium Fourier Transform                                                           |              |                           |
| SPACE             | Sampling Perfection with Application optimized Contrasts using different flip-angle Evolutions | SE+3D+PF+ZF  | Siemens                   |
| CUBE              |                                                                                                | SE+3D+PF+ZF  | GE                        |
| VISTA             | Volume ISotropic Turbo spin echo Acquisition                                                   | SE+3D+PF+ZF  | Philips                   |
| isoFSE            | ISOtropic Fast Spin Echo                                                                       | SE+3D+PF+ZF  | Hitachi                   |
| EPI               | Echo Planar Imaging                                                                            | EP           | All                       |
| TGSE              | Turbo Gradient Spin Echo                                                                       | GR+SE        | Siemens                   |
| GRASE             | Gradient And Spin Echo                                                                         | GR+SE        | Philips                   |
| PACE              | Prospective Acquisition CorrEction                                                             |              | Siemens                   |
| BLADE             |                                                                                                |              | Siemens                   |
| PROPELLER         | Periodically Rotated Overlapping ParallEL Lines with Enhanced Reconstruction                   |              | GE                        |
| RADAR             | RADial Aquisition Regime                                                                       |              | Hitachi                   |
| JET               |                                                                                                |              | Toshiba                   |
| BRAVO             | BRAin VOlume imaging                                                                           |              | GE                        |
| COSMIC            | Coherent Oscillatory State Acquisition for Manipulation of Imaging Contrast                    |              | GE                        |
| FAME              | Fast Acquisition with Multiphase Elliptical fast gradient ech                                  |              | GE                        |
| MENSA             | Multi-Echo iN Steady-state Acquisition                                                         |              | GE                        |
|                   | **Option acronyms**                                                                            |              |                           |
| SENSE             | SENSitivity Encoding                                                                           |              | Philips                   |
| mSENSE            | Modified SENSitivity Encoding                                                                  |              | Siemens                   |
| ASSET             | Array coil Spatial Sensitivity Encoding                                                        |              | GE                        |
| GRAPPA            | GeneRalized Autocalibrating Partial Parallel Acquisition                                       |              | Siemens                   |
| ARC               | Autocalibrating Reconstruction for Cartesian imaging                                           |              | GE                        |
| NEX               | Number Of Excitations                                                                          |              | GE                        |
| NSA               | Number of Signal Averages                                                                      |              | Philips, Hitachi, Toshiba |
| POMP              | Phase-Offset MultiPlanar                                                                       |              | GE                        |
| CLEAR             | Constant LEvel AppeaRance                                                                      |              | Philips                   |
| TONE              | Tilt-Optimized Nonsaturated Excitation                                                         |              | Siemens, Philips          |
| SSP               | Sloped Slab Profile -                                                                          |              | Hitachi                   |
| ISCE              | Inclined Slab for Contrast Enhancement                                                         |              | Toshiba                   |
| MTC               | Magnetization Transfer Contrast                                                                |              | All                       |
| SORS-STC          | Slice-selective Off-Resonance Sinc Saturation Transfer Contrast                                |              | Toshiba                   |
| MSOFT             | MultiSection Off-resonance Fat-suppression Technique                                           |              | Toshiba                   |
| SPIR              | Spectral Presaturation with Inversion Recovery                                                 |              | Philips                   |
| IDEAL             | Iterative Decomposition of water and fat with Echo Asymmetry and Least-squares estimation      |              | GE                        |
| PASTA             | Polarity-Altered Spectral and spaTial selective Acquisition                                    |              | Toshiba                   |
| REST              | REgional Saturation Technique                                                                  |              | Philips                   |
| BFAST             | Blood Flow Artifact Suppression Technique                                                      |              | Toshiba                   |
| PURE              | Phased array Uniformity Enhancement                                                            |              | GE                        |
| NATURAL           | NATural Uniformity Realization Algorithm                                                       |              | Hitachi                   |
| SCIC              | Surface Coil Intensity Correction                                                              |              |                           |
| CENTRA            | Contrast-ENhanced Timing Robust Angiography                                                    |              | Philips                   |
| PEAKS             | PEak Arterial K-Space filling                                                                  |              | Hitachi                   |
| DRKS              | Differential Rate K-space Sampling                                                             |              | Toshiba                   |
|                   |                                                                                                |              |                           |


## SIEMENS sequence names

This table contains a list of SIEMENS vendor sequences that I found in
various protocols, along with the general sequence type they correspond to.
The software versions listed are not exhaustive -- these are only those
for which I have _seen_ a protocol from that version with the corresponding
sequence.

From my understanding, `gre*` (GRE) sequences are not explicitely spoiled, while
`*fl*` (FLASH) sequences always have a spoiler gradient and have the option
to further apply RF spoiling.

The `spc*` (SPACE) sequences are SIEMENS-specific variants of `tse` (Turbo
Spin Echo) that use 3D spatial encoding, partial fourier and k-space zero
filling.


| Sequence          | Full Name                     | Versions           | Base  | Sequence Type(s)  | Special | Used for    | Options   |
| ----------------- | ----------------------------- | ------------------ | ----- | ----------------- | ------- | ----------- | --------- |
| gre               | GradientEcho                  | VA, VD, VB, VE, XA | GR    | GRE               |         | loc, smap   |           |
| gre_field_mapping | Gradient Echo Field Mapping   | VB                 | GR    | GRE               | 2TE     | fmap        |           |
| fl                | FLASH                         | VD, VB, VE         | GR    | GRE/SPGR          | GSP     | loc         | RFSP      |
| fl_r              | FLASH ?                       | VD, VB, VE         | GR    | SWI               | GSP     | swi         | RFSP, 2TE |
| fl_rr             | FLASH ?                       |                    | GR    |                   |         |             |           |
| tfl               | TurboFLASH                    | VD, VB, VE         | GR    | SPGR              | GSP     | mprage, vfa | RFSP, MP  |
| fm_r              | Field Mapping                 | VE                 | GR    | GRE               | 2TE     | fmap        | RFSP      |
| tse               | Turbo Spin Echo               | VA, VD, VB, VE     | SE    | TSE               |         | T2, T2w     | ME        |
| tse_vfl           | Turbo Spin Echo Variable Flip | VB                 | SE    | TSE Variable Flip |         | T2w, flair  | MP        |
| spc               | SPACE                         | VD, VE             | SE    | SPACE             |         | T2w         |           |
| spcir             | SPACE-IR                      | VD, VE             | SE    | SPACE-IR          |         | flair       |           |
| spcR              | SPACE-RESTORE                 | VD                 | SE    | SPACE-DE          |         | flair       |           |
| fl_tof            | FLASH-ToF                     | VB                 | GR    | ToF               |         | tof         |           |
| tfi               | TRUFI/TrueFISP                | VD                 | GR    | bSSFP             |         |             |           |
| tgse              | Turbo Gradient Spin Echo      | VE                 | SE/GR | TSE/GE            |         | asl         |           |
| swi_r             | SWI                           | VA                 | GR    |                   |         | swi         |           |
| epfid             | EPI-FID                       | VD                 | GR    | GRE-EPI           |         | bold        |           |
| epse              | EPI-SE                        | VD                 | SE    | SE-EPI            |         | dwi, dti    |           |
| ep2d_fid          | EPI-FID                       | VB, VE             | GR    | GRE-EPI           |         | bold        |           |
| ep2d_bold         | EPI-BOLD                      | VB, VE             | GR    | GRE-EPI           | BOLD    | bold        |           |
| ep2d_pasl         | EPI-PASL                      | VB, VE             | GR    | GRE-EPI           |         | pasl        |           |
| ep2d_pace         | EPI-PACE                      | VB, VE             | GR    | GRE-EPI           | PMC     | bold        |           |
| ep2d_diff         | EPI-Diffusion                 | VB, VE             | SE    | SE-EPI            |         | dwi, dti    |           |
