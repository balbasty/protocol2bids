import fnmatch
from operator import truediv
from protocol2bids.utils.nii2axes import nii2axes


def _error(*a, **k):
    raise RuntimeError(*a, **k)


def _get(mapping, key, *default):
    """
    Get element from nested dictionary, with "//" separating levels
    """
    try:
        key = list(key.split("//"))
        while key:
            mapping = mapping[key.pop(0)]
    except Exception:
        if default:
            return default[0]
        else:
            raise
    return mapping


def _guess_fe_direction(pe, se, s, c, t):
    se = {
        "Sagittal": s[0] + s[-1],
        "Transversal": {"FH": "IS", "HF": "SI"}[t[0] + t[-1]],
        "Coronal": c[0] + c[-1],
    }[se]
    pe = pe[0] + pe[-1]
    if pe in ("LR", "RL"):
        if se in ("PA", "AP"):
            fe = "Transversal"
        else:
            assert se in ("IS", "SI")
            fe = "Coronal"
    elif pe in ("PA", "AP"):
        if se in ("LR", "RL"):
            fe = "Transversal"
        else:
            assert se in ("IS", "SI")
            fe = "Sagittal"
    else:
        assert pe in ("IS", "SI")
        if se in ("LR", "RL"):
            fe = "Coronal"
        else:
            assert se in ("AP", "PA")
            fe = "Sagittal"
    fe = {
        "Sagittal": s[0] + s[-1],
        "Transversal": {"FH": "IS", "HF": "SI"}[t[0] + t[-1]],
        "Coronal": c[0] + c[-1],
    }[fe]
    return fe


VARIANTS = {
    "Orientation": (
        "Routine//Orientation",
        "Routine//Slab group 1//Orientation",
        "Routine//Slice group 1//Orientation",
    ),
    "Phase enc. dir.": (
        "Routine//Slab group 1//Phase enc. dir.",     # VB,VE
        "Routine//Slice group 1//Phase enc. dir.",    # VB,VE
        "Routine//Phase enc. dir.",                  # VD
        "Geometry//Phase enc. dir.",                 # VD
    ),
    "System//Sagittal": (
        "System//Sagittal",                          # VD,VB
        "System - Miscellaneous//Sagittal",          # VE
    ),
    "System//Coronal": (
        "System//Coronal",                           # VD,VB
        "System - Miscellaneous//Coronal",           # VE
    ),
    "System//Transversal": (
        "System//Transversal",                       # VD,VB
        "System - Miscellaneous//Transversal",       # VE
    ),
}


KEYMAP_BASIC = {
    # NOTE
    #   BIDS has the key "PhaseEncodingDirection" which must take value
    #   {"i", "i-", "j", "j-", "k", "k-"}
    #
    #   We introduce our own keyword(s) "DirectionPE", "DirectionFE",
    #   "DirectionSE" (corresponding to BIDS (potential) keywords
    #   "PhaseEncodingDirection", "FrequencyEncodingDirection" and
    #   "SliceEncodingDirection"), which take value in
    #   {"LR", "RL", "AP", "PA", "IS", "SI"}
    #
    #   We like these values because BIDS values can be derived from these
    #   + the nifti"s affine matrix. They are also more robust to potential
    #   reorganisations of the voxel layout.
    "DirectionSE": {
        "args": [
            VARIANTS["Orientation"],
            VARIANTS["System//Sagittal"],
            VARIANTS["System//Coronal"],
            VARIANTS["System//Transversal"],
        ],
        "formula": lambda x, s, c, t: {
            "Sagittal": s[0] + s[-1],
            "Transversal": {"FH": "IS", "HF": "SI"}[t[0] + t[-1]],
            "Coronal": c[0] + c[-1],
        }[x]
    },
    "DirectionPE":  {
        "args": [VARIANTS["Phase enc. dir."]],
        "formula": lambda x: x[0] + x[-1],
    },
    "DirectionFE": {
        "args": [
            VARIANTS["Phase enc. dir."],
            VARIANTS["Orientation"],
            VARIANTS["System//Sagittal"],
            VARIANTS["System//Coronal"],
            VARIANTS["System//Transversal"],
        ],
        "formula": _guess_fe_direction
    },
}


KEYMAP_CLASSIC = {
    # ==================================================================
    #   BIDS
    # ==================================================================

    # ------------------------------------------------------------------
    #   MRIHardware
    # ------------------------------------------------------------------
    "Manufacturer": {"args": [], "formula": lambda: "Siemens"},
    "ManufacturersModelName": "Header//ModelName",
    "SoftwareVersions": "Header//SoftwareVersions",
    "MagneticFieldStrength": {
        "args": ["Header//ModelName"],
        "formula": lambda x: {
            "Aera": 1.5,
            "Altea": 1.5,
            "Amira": 1.5,
            "Avanto": 1.5,
            "Avanto_fit": 1.5,
            "Cima X": 3.0,
            "EspreeTim": 1.5,
            "EssenzaTim": 1.5,
            "Flow": 1.5,
            "Harmony": 1.0,
            "Lumina": 3.0,
            "Mica": 1.5,
            "Prisma": 3.0,
            "Prisma_fit": 3.0,
            "Seara": 3.0,
            "Sempra": 1.5,
            "Skyra": 3.0,
            "Skyra_fit": 3.0,
            "Sola": 1.5,
            "Sola_fit": 1.5,
            "Sonata": 1.5,
            "Spectra": 3.0,
            "Symphony": 1.5,
            "Terra": 7.0,
            "Terra X": 7.0,
            "TrioTim": 3.0,
            "VerioTim": 3.0,
            "Vida": 3.0,
            "Vida_fit": 3.0,
        }[x]
    },
    # "ReceiveCoilName": None,
    "ReceiveCoilActiveElements": "Routine//Coil elements",
    # "GradientSetType": None,
    # "MRTransmitCoilSequence": None,
    "MatrixCoilMode": (
        # only present in VB
        "Resolution//Matrix Coil Mode",
    ),
    "CoilCombinationMethod": {
        "args": [(
            "System//Coil Combine Mode",
            "System - Miscellaneous/Coil Combine Mode",
            "System - Miscellaneous/Coil Combination",
        )],
        "formula": lambda x: {
            "Sum of Squares": "rSOS",
            "Adaptive Combine": "adaptive",
        }.get(x, x)
    },

    # ------------------------------------------------------------------
    #   MRIInstitutionInformation
    # ------------------------------------------------------------------
    # "InstitutionName": None,
    # "InstitutionAddress": None,
    # "InstitutionalDepartmentName": None,

    # ------------------------------------------------------------------
    #   MRISequenceSpecifics
    # ------------------------------------------------------------------
    "PulseSequenceType": [
        # Multiband EPI
        {
            "args": [
                (
                    "Header//SequenceName",
                    "Sequence - Part 1//Sequence Name",
                ),
                "Routine//Multi-band accel. factor"
            ],
            "formula": lambda x, mb: ("Multiband " if int(mb) > 1 else "") + {
                "ep2d_fid": "Gradient Echo EPI",
                "ep2d_bold": "Gradient Echo EPI",
                "ep2d_pace": "Gradient Echo EPI",
                "ep2d_pasl": "Gradient Echo EPI",
                "ep2d_diff": "Spin Echo EPI",
                "epfid": "Gradient Echo EPI",
                "epse": "Spin Echo EPI",
            }[x]
        },
        # MPRAGE
        {
            "args": [
                (
                    "Header//SequenceName",
                    "Sequence - Part 1//Sequence Name",
                ),
                (
                    "Contrast//TI",
                    "Contrast - Common//TI"
                )
            ],
            "formula": lambda x, _: {
                "tfl": "MPRAGE",
            }[x]
        },
        # Spoiled Gradient Echo
        {
            "args": [
                (
                    "Header//SequenceName",
                    "Sequence - Part 1//Sequence Name",
                ),
                (
                    "Sequence//RF Spoiling",
                    "Sequence - Part 2//RF Spoiling"
                )
            ],
            "formula": lambda x, sp: ("Spoiled " if sp == "On" else "") + {
                "gre": "Gradient Echo",
                "gre_field_mapping": "Gradient Echo",
                "fm_r": "Gradient Echo",
                "fl": "Gradient Echo",
                "fl_r": "Gradient Echo",
                "fl_rr": "Gradient Echo",
                "fl_tof": "Gradient Echo",
                "tfl": "Gradient Echo",
                "epfid": "Gradient Echo EPI",
                "ep2d_fid":  "Gradient Echo EPI",
                "ep2d_bold":  "Gradient Echo EPI",
                "ep2d_pace":  "Gradient Echo EPI",
            }[x]
        },
        # Everything else
        {
            "args": [(
                "Header//SequenceName",
                "Sequence - Part 1//Sequence Name",
            )],
            "formula": lambda x: {
                "gre": "Gradient Echo",
                "gre_field_mapping": "Gradient Echo",
                "fm_r": "Gradient Echo",
                "fl": "Gradient Echo",
                "fl_r": "Gradient Echo",
                "fl_rr": "Gradient Echo",
                "fl_tof": "Gradient Echo",
                "tfl": "Gradient Echo",
                "epfid": "Gradient Echo EPI",
                "ep2d_fid":  "Gradient Echo EPI",
                "ep2d_bold":  "Gradient Echo EPI",
                "ep2d_pace":  "Gradient Echo EPI",
                "ep2d_pasl":  "PASL - Gradient Echo EPI",
                "spc": "T2-SPACE",
                "spcir": "FLAIR",
                "spcR": "Driven Equilibrium T2-SPACE",
                "epse": "Spin Echo EPI",
                "ep2d_diff": "Spin Echo EPI",
                "tse": "Fast Spin Echo",
                "tse_vfl": "Fast Spin Echo + Variable Flip",
                "tfi": "bSSFP",
                "swi_r": "Susceptibility Weighted Gradient Echo",
                "tgse": "Gradient And Spin Echo",
            }[x]
        },
    ],
    "ScanningSequence": [
        # Gradient Echo // Spin Echo
        {
            "args": ["Header//SequenceName"],
            "formula": lambda x: {
                "gre": ["GR"],                  # Gradient Echo
                "gre_field_mapping": ["GR"],    # Gradient Echo Field Mapping
                "fm_r": ["GR"],                 # Field Mapping
                "fl": ["GR"],                   # FLASH
                "fl_r": ["GR"],                 # FLASH
                "fl_rr": ["GR"],                # FLASH
                "fl_tof": ["GR"],               # FLASH Time of Flight
                "tfl": ["GR"],                  # TurboFLASH
                "epfid": ["GR", "EP"],          # Echo-planar GRE
                "ep2d_fid": ["GR", "EP"],       # Echo-planar GRE
                "ep2d_bold": ["GR", "EP"],      # Echo-planar GRE (+ BOLD card)
                "ep2d_pace": ["GR", "EP"],      # Echo-planar GRE (+ MoCO)
                "ep2d_pasl": ["GR", "EP"],      # Echo-planar GRE (+ PASL)
                "spc": ["SE"],                  # SPACE
                "spcir": ["SE", "IR"],          # SPACE Inversion Recovery
                "spcR": ["SE"],                 # SPACE + RESTORE
                "epse": ["SE", "EP"],           # Echo-planar Spin Echo
                "ep2d_diff": ["SE", "EP"],      # Echo-planar Diffusion
                "tse": ["SE"],                  # Turbo Spin Echo
                "tse_vfl": ["SE"],              # Turbo Spin Echo Variable Flip
                "tfi": ["GR"],                  # TRUFI
                "swi_r": ["GR"],                # Susceptibility Weighted
                "tgse": ["GR", "SE"],           # Turbo Gradient Spin Echo
            }[x],
            "iadd": True,
        },
        # Inversion recovery
        {
            "args": [(
                "Contrast//TI",
                "Contrast - Common//TI"
            )],
            "formula": lambda _: ["IR"],
            "iadd": True,
        },
    ],
    "SequenceVariant": [
        # OverSampling Phase
        {
            "args": ["Routine//Phase oversampling"],
            "formula": lambda x: ["PO"] if int(x.split()[0]) > 0 else [],
            "iadd": True,
        },
        # Steady State
        {
            "args": ["Header//SequenceName"],
            "formula": lambda x: {"tfi": ["SS"]}[x],
            "iadd": True,
        },
        # Magnetization Prepared
        {
            "args": [(
                "Contrast//TI",
                "Contrast - Common//TI"
            )],
            "formula": lambda _: ["MP"],
            "iadd": True,
        },
        # RF Spoiling
        {
            "args": [(
                "Sequence//RF Spoiling",
                "Sequence - Part 2//RF Spoiling"
            )],
            "formula": lambda x: ["SP"] if x == "On" else [],
            "iadd": True,
        },
    ],
    "ScanOptions": [
        # Fat Saturation
        {
            "args": [(
                "Contrast//Fat suppr.",
                "Contrast - Common//Fat suppr."
            )],
            "formula": lambda x: [] if x == "None" else ["FS"],
            "iadd": True,
        },
        # Partial Fourier - Frequency
        {
            "args": [(
                "Sequence//Asymmetric echo",
                "Sequence - Part 1//Asymmetric echo",
            )],
            "formula": lambda x: ["PFF"] if x != "Off" else [],
            "iadd": True,
        },
        # Partial Fourier - Phase
        {
            "args": [(
                "Resolution//Phase partial Fourier",
                "Resolution - Acceleration//Phase partial Fourier",
            )],
            "formula": lambda x: ["PFP"] if x != "Off" else [],
            "iadd": True,
        },
        # Flow Compensation
        {
            "args": [(
                "Sequence//Flow comp.",
                "Sequence//Flow comp. 1",
                "Sequence - Part 1//Flow compensation",
            )],
            "formula": lambda x: ["FC"] if x != "No" else [],
            "iadd": True,

        },
    ],
    "SequenceName": [
        {
            "args": [(
                "Header//SequenceName",
                "Sequence - Part 1//Sequence Name"
            )],
            "formula": lambda x: x,
        },
    ],
    # "PulseSequenceDetails": None,
    # "NonlinearGradientCorrection": None,
    "MRAcquisitionType": (
        "Sequence//Dimension",
        "Sequence - Part 1//Dimension",
    ),
    # ------------------------------------------------------------------
    #   MTParameters
    # ------------------------------------------------------------------
    # "MTState": None,
    # "MTOffsetFrequency": None,
    # "MTPulseBandwidth": None,
    # "MTNumberOfPulses": None,
    # "MTPulseShape": None,
    # "MTPulseDuration": None,
    # "SpoilingState": None,
    # "SpoilingType": None,
    # "SpoilingRFPhaseIncrement": None,
    # "SpoilingGradientMoment": None,
    # "SpoilingGradientDuration": None,

    # ------------------------------------------------------------------
    #   MRISpatialEncoding
    # ------------------------------------------------------------------
    # "NumberShots": None,
    "ParallelReductionFactorInPlane": {
        "args": [(
            "Resolution//Accel. factor PE",
            "Resolution - iPAT//Accel. factor PE",
            "Resolution - Acceleration//Acceleration factor PE",
        )],
        "formula": lambda x: int(x)
    },
    "ParallelReductionFactorOurOfPlane": {
        "args": [(
            "Resolution//Accel. factor 3D",
            "Resolution - iPAT//Accel. factor 3D",
            "Resolution - Acceleration//Acceleration factor 3D",
        )],
        "formula": lambda x: int(x)
    },
    "ParallelAcquisitionTechnique": {
        "args": [(
            "Resolution//PAT mode",
            "Resolution - iPAT//PAT mode",
            "Resolution - Acceleration//Acceleration mode",
        )],
        "formula": lambda x: _error() if x == "Off" else x
    },
    # "PartialFourier": None,
    # "PartialFourierDirection": None,
    # "EffectiveEchoSpacing": raise ValueError("Done in special"),
    # "MixingTime": None,
    # "PhaseEncodingDirection": raise ValueError("Done before"),
    # "TotalReadoutTime": raise ValueError("Done in special"),

    # ------------------------------------------------------------------
    #   MRITimingParameters
    # ------------------------------------------------------------------
    "EchoTime": {
        "args": ["Routine//TE"],
        "formula": lambda x: float(x.split()[0]) * 1e-3,
    },
    "InversionTime": {
        "args": [(
            "Contrast//TI",
            "Contrast - Common//TI",
        )],
        "formula": lambda x: float(x.split()[0]) * 1e-3,
    },
    "DwellTime": {
        "args": [
            (
                "Sequence//Bandwidth",
                "Sequence - Part 1//Bandwidth",
            ),
            (
                "Resolution//Base resolution",
                "Resolution - Common//Base resolution"
            )
        ],
        "formula": lambda x, y: 1/(float(x.split()[0])*int(y))
    },
    # "SliceTiming": None,
    # "SliceEncodingDirection": raise ValueError("Done before"),

    # ------------------------------------------------------------------
    #   MRIRFandContrast
    # ------------------------------------------------------------------
    "FlipAngle": {
        "args": [(
            "Contrast//Flip angle",
            "Contrast - Common//Flip angle",
        )],
        "formula": lambda x: float(x.split()[0]),
    },
    # "NegativeContrast": None,

    # ------------------------------------------------------------------
    #   MRISliceAcceleration
    # ------------------------------------------------------------------
    "MultibandAccelerationFactor": {
        "args": ["Routine//Multi-band accel. factor"],
        "formula": int
    },

    # ==================================================================
    #   DCM2NIIX
    # ==================================================================

    # ------------------------------------------------------------------
    #   GlobalConstants
    # ------------------------------------------------------------------
    "Modality": {"args": [], "formula": lambda: "MR"},
    # "ConversionSoftware": None,
    # "ConversionSoftwareVersion": None,

    # ------------------------------------------------------------------
    #   GlobalSeriesInformation
    # ------------------------------------------------------------------
    # "BodyPartExamined": None,
    # "PatientPosition": None,
    # "ProcedureStepDescription": None,
    # "SeriesDescription": None,
    # "ProtocolName": None,
    "ImageType": {"args": [], "formula": lambda: ["ORIGINAL", "PRIMARY"]},
    # "AcquisitionTime": None,
    # "AcquisitionNumber": None,
    # "ImageComments": None,

    # ------------------------------------------------------------------
    #   ModalityMagneticResonanceImaging
    # ------------------------------------------------------------------
    "AcquisitionMatrixPE": {
        "args": [
            (
                "Resolution//Base resolution",              # VD,VB
                "Resolution - Common//Base resolution",     # VE
            ),
            (
                "Resolution//Phase resolution",             # VD,VB
                "Resolution - Common//Phase resolution",    # VE
            ),
            "Routine//FoV phase",
        ],
        "formula": lambda base, ph, fov:
            int(round(
                int(base) *
                (float(ph.split()[0]) / 100) *
                (float(fov.split()[0]) / 100)
            ))
    },
    "VendorReportedEchoSpacing": {
        "args": [(
            "Sequence//Echo spacing",
            "Sequence - Part 1//Echo spacing"
        )],
        "formula": lambda x: float(x.split()[0]) * 1e-3
    },
    # "EchoNumber": None,
    # "EstimatedEffectiveEchoSpacing": raise ValueError("Done in special"),
    # "EstimatedTotalReadoutTime": raise ValueError("Done in special"),
    # "VariableFlipAngleFlag": None,
    # "ImageOrientationPatientDICOM": None,
    "ImagingFrequency": {
        "args": [(
            "System//Frequency 1H",
            "System - Tx/Rx//Frequency 1H",
        )],
        "formula": lambda x: float(x.split()[0])
    },
    # "InPlanePhaseEncodingDirectionDICOM": None,
    "NumberOfAverages": {
        "args": ["Routine//Averages"],
        "formula": int,
    },
    "PercentPhaseFOV": {
        "args": ["Routine//FoV Phase"],
        "formula": lambda x: float(x.split()[0])
    },
    # "PercentSampling": None,
    "FrequencyEncodingSteps": {
        "args": ["OversampledAcquisitionMatrixPE", "PartialFourierFE"],
        "formula": lambda x, y: int(round(x * y))
    },
    "PhaseEncodingSteps": {
        "args": ["OversampledAcquisitionMatrixPE", "PartialFourierPE"],
        "formula": lambda x, y: int(round(x * y))
    },
    "PhaseEncodingStepsOutOfPlane": {
        "args": ["OversampledAcquisitionMatrixSE", "PartialFourierSE"],
        "formula": lambda x, y: int(round(x * y))
    },
    "PixelBandwidth": {
        "args": [(
            "Sequence//Bandwidth",
            "Sequence - Part 1//Bandwidth",
        )],
        "formula": lambda x: float(x.split()[0])
    },
    # "RepetitionTimeInversion": None,
    # "SAR": None,
    "SliceThickness": {
        "args": ["Routine//Slice thickness"],
        "formula": lambda x: float(x.split()[0]),
    },
    "SpacingBetweenSlices": [
        {
            "args": [
                "Routine//Slice thickness",
                "Routine//Slice group 1//Dist. factor"
            ],
            "formula": lambda x, y:
                float(x.split()[0]) * (1 + float(y.split()[0])),
        },
        {
            "args": ["Routine//Slice thickness"],
            "formula": lambda x: float(x.split()[0]),
        },
    ],

    # ==================================================================
    #   PROTOCOL2BIDS
    # ==================================================================

    # ------------------------------------------------------------------
    #   SEQUENCE
    # ------------------------------------------------------------------
    "EchoPulseSequence": {
        "args": ["ScanningSequence"],
        "formula": lambda x: (
            "BOTH" if "GR" in x and "SE" in x else
            "GRADIENT" if "GR" in x else
            "SPIN" if "SE" in x else
            _error()
        )
    },
    "MultipleSpinEcho": {
        "args": ["SequenceName"],
        "formula": lambda x: "tse" in x or "spc" in x
    },
    "MultiPlanarExcitation": [
        # multiband
        {
            "args": ["Routine//Multi-band accel. factor"],
            "formula": lambda x: x > 1
        },
        # default
        {
            "args": [],
            "formula": lambda x: False,
        }
    ],
    # "PhaseContrast": None,
    # "VelocityEncodingDirection": None,
    "TimeOfFlightContrast": [
        {
            "args": [(
                "Angio//TONE ramp",
                "Angio - Common//TONE ramp",
            )],
            "formula": lambda _: True,
        },
        {
            "args": ["SequenceName"],
            "formula": lambda x: "tof" in x
        },
    ],
    "ArterialSpinLabelingContrast": {
        "args": ["SequenceName"],
        "formula": lambda x: "PULSED" if "pasl" in x else "NONE"
    },
    "SteadyStatePulseSequence": {
        "args": ["SequenceName"],
        "formula": lambda x: "FREE_PRECESSION" if "tfi" in x else "NONE"
        # FIXME!!!
    },
    "EchoPlanarPulseSequence": {
        "args": ["ScanningSequence"],
        "formula": lambda x: "EP" in x
    },
    # "SaturationRecovery": None,
    # "SpectrallySelectedSuppression": None,
    "OversamplingPhase": {
        "args": ["Routine//Slice oversampling", "Routine//Phase oversampling"],
        "formula": lambda sl, ph: (
            "2D_3D" if float(ph.split()[0]) and float(sl.split()[0]) else
            "2D" if float(ph.split()[0]) else
            "3D" if float(sl.split()[0]) else
            "NONE"
        )
    },
    # ------------------------------------------------------------------
    #   TRAJECTORY
    # ------------------------------------------------------------------
    "GeometryOfKSpaceTraversal": {
        # As far as I know, all vendor sequences are cartesian
        "args": [],
        "formula": lambda: "RECTILINEAR"
    },
    # "SegmentedKSpaceTraversal": None,
    "RectilinearPhaseEncodeReordering": [
        {
            "args": [(
                "Sequence//Reordering",
                "Sequence - Part 1//Reordering",
                "Contrast - Dynamic//Reordering",
            )],
            "formula": lambda x: {
                "Linear": "LINEAR",
                "Centric": "CENTRIC"
            }[x]
        },
        {
            "args": [(
                "Inline - Common//3D centric reordering",
                "Angio//3D centric reordering",
                "Angio - Common//3D centric reordering",
            )],
            "formula": lambda x: "CENTRIC" if x != "Off" else "LINEAR"
        },
    ],
    # "NumberOfKSpaceTrajectories": None,
    # "CoverageOfKSpace": None,
    # "EchoTrainLength": None,
    # ------------------------------------------------------------------
    #   ???
    # ------------------------------------------------------------------
    "SliceGap": [
        {
            "args": [
                "Routine//Slice thickness",
                "Routine//Slice group 1//Dist. factor"
            ],
            "formula": lambda x, y:
                float(x.split()[0]) * float(y.split()[0]),
        },
        {
            "args": [],
            "formula": lambda: 0.0,
        },
    ],
    # ------------------------------------------------------------------
    #   TIMING / CONTRAST
    # ------------------------------------------------------------------
    "VendorReportedRepetitionTime": {
        "args": ["Routine//TR"],
        "formula": lambda x: float(x.split()[0]) * 1e-3,
    },
    "SliceOrder": "Geometry//Series",
    # ------------------------------------------------------------------
    #   PARTIAL FOURIER
    # ------------------------------------------------------------------
    "HasPartialFourierFE": {
        "args": ["Sequence//Asymmetric echo"],
        "formula": lambda x: x != "Off"
    },
    "HasPartialFourierPE": {
        "args": ["Resolution//Phase partial Fourier"],
        "formula": lambda x: x != "Off"
    },
    "HasPartialFourierSE": {
        "args": ["Resolution//Slice partial Fourier"],
        "formula": lambda x: x != "Off"
    },
    "PartialFourierPE": {
        "args": ["Resolution//Phase partial Fourier"],
        "formula": lambda x: truediv(*map(float, x.split("/")))
    },
    "PartialFourierSE": {
        "args": ["Resolution//Slice partial Fourier"],
        "formula": lambda x: truediv(*map(float, x.split("/")))
    },
    # ------------------------------------------------------------------
    #   MATRIX
    # ------------------------------------------------------------------
    "AcquisitionMatrixFE": {
        "args": ["Resolution//Base resolution"],
        "formula": int,
    },
    "AcquisitionMatrixSE": [
        # As far as I know, only localizers have more than one slice//slab
        # group, so we only care about the first group.
        # --------------------------------------------------------------
        #   3D
        # --------------------------------------------------------------
        {
            "args": [
                "Routine//Slab group 1//Slabs",
                "Routine//Slices per slab",
            ],
            "formula": lambda slabs, slices: int(slabs) * int(slices)
        },
        {
            "args": [
                "Routine//Slabs",
                "Routine//Slices per slab",
            ],
            "formula": lambda slabs, slices: int(slabs) * int(slices)
        },
        {
            "args": [
                "Geometry//Slabs",
                "Geometry//Slices per slab",
            ],
            "formula": lambda slabs, slices: int(slabs) * int(slices)
        },
        {
            "args": [
                "Geometry//Slab group 1//Slabs",
                "Geometry//Slices per slab",
            ],
            "formula": lambda slabs, slices: int(slabs) * int(slices)
        },
        # --------------------------------------------------------------
        #   2D
        # --------------------------------------------------------------
        {
            "args": ["Routine//Slice group 1//Slices"],
            "formula": int,
        },
        # ?
        {
            "args": ["Geometry//Slice group 1//Slices"],
            "formula": int,
        },
        {
            "args": ["Routine//Slices"],
            "formula": int,
        },
        {
            "args": ["Geometry//Slices"],
            "formula": int,
        },
    ],
    "OversampledAcquisitionMatrixFE": {
        "args": ["AcquisitionMatrixFE"],
        "formula": lambda x: 2*x  # FIXME: is it always the case?
    },
    "OversampledAcquisitionMatrixPE": {
        "args": [
            "Resolution//Base resolution",
            "Resolution//Phase resolution",
            "Routine//FoV phase",
            "Routine//Phase oversampling",
        ],
        "formula": lambda base, ph, fov, po:
            int(round(
                int(base) *
                (float(ph.split()[0]) / 100) *
                (float(fov.split()[0]) / 100) *
                (1 + (float(po.split()[0]) / 100))
            ))
    },
    "OversampledAcquisitionMatrixSE": [
        # As far as I know, only localizers have more than one slice//slab
        # group, so we only care about the first group.
        # --------------------------------------------------------------
        #   3D
        # --------------------------------------------------------------
        {
            "args": [
                "Routine//Slab group 1//Slabs",
                "Routine//Slices per slab",
                "Routine//Slice oversampling",
            ],
            "formula": lambda slabs, slices, os: int(round(
                int(slabs) * int(slices) * (1 + float(os.split()[0]))
            ))
        },
        {
            "args": [
                "Routine//Slabs",
                "Routine//Slices per slab",
                "Routine//Slice oversampling",
            ],
            "formula": lambda slabs, slices, os: int(round(
                int(slabs) * int(slices) * (1 + float(os.split()[0]))
            ))
        },
        {
            "args": [
                (
                    "Geometry//Slabs",
                    "Geometry - Common//Slabs"
                ),
                (
                    "Geometry//Slices per slab",
                    "Geometry - Common//Slices per slab"
                ),
                (
                    "Geometry//Slice oversampling",
                    "Geometry - Common//Slice oversampling"
                ),
            ],
            "formula": lambda slabs, slices, os: int(round(
                int(slabs) * int(slices) * (1 + float(os.split()[0]))
            ))
        },
        {
            "args": [
                (
                    "Geometry//Slab group 1//Slabs",
                    "Geometry - Common//Slabs"
                ),
                (
                    "Geometry//Slices per slab",
                    "Geometry - Common//Slices per slab"
                ),
                (
                    "Geometry//Slice oversampling",
                    "Geometry - Common//Slice oversampling"
                ),
            ],
            "formula": lambda slabs, slices, os: int(round(
                int(slabs) * int(slices) * (1 + float(os.split()[0]))
            ))
        },
        # --------------------------------------------------------------
        #   2D
        # --------------------------------------------------------------
        {
            "args": ["Routine//Slice group 1//Slices"],
            "formula": int,
        },
        {
            "args": [(
                "Geometry//Slice group 1//Slices",
                "Geometry - Common//Slice group 1//Slices",
            )],
            "formula": int,
        },
        {
            "args": ["Routine//Slices"],
            "formula": int,
        },
        {
            "args": ["Geometry//Slices"],
            "formula": int,
        },
    ],
    # ------------------------------------------------------------------
    #   FOV
    # ------------------------------------------------------------------
    "FieldOfViewFE": {
        "args": ["Routine//FoV read"],
        "formula": lambda x: float(x.split()[0])
    },
    "FieldOfViewPE": {
        "args": ["Routine//FoV read", "Routine//FoV phase"],
        "formula": lambda x, y: float(x.split()[0]) * float(y.split()[0]) / 100
    },
    "FieldOfViewSE": {
        "args": ["AcquisitionMatrixSE", "SpacingBetweenSlices"],
        "formula": lambda x, y: x*y
    },
}

KEYMAP_SPECIAL = {}

# TurboFLASH (= MPRAGE)
KEYMAP_SPECIAL["tfl*"] = {
    "RepetitionTimePreparation": "VendorReportedRepetitionTime",
    "RepetitionTimeInversion": "VendorReportedRepetitionTime",
    "RepetitionTimeExcitation": "VendorReportedEchoSpacing",
}
# FLASH (= SPGR)
KEYMAP_SPECIAL["fl*"] = {
    "RepetitionTimeExcitation": "VendorReportedRepetitionTime",
}
# GRE
KEYMAP_SPECIAL["gre*"] = {
    "RepetitionTimeExcitation": "VendorReportedRepetitionTime",
}
# TRUFI (= bSSFP)
KEYMAP_SPECIAL["tfi*"] = {
    "RepetitionTimeExcitation": "VendorReportedRepetitionTime",
}
# EPI
KEYMAP_SPECIAL["ep*"] = {
    # This is the bandwidth across the PE direction,
    # in reference to the "apparent" acquisition matrix
    # (`AcquisitionMatrixPE`), not the "true" acquisition matrix
    # (`OversampledAcquisitionMatrixPE`)
    "BandwidthPerPixelPhaseEncode": {
        "args": [
            "VendorReportedEchoSpacing",
            "ReconMatrixPE",
            "ParallelReductionFactorInPlane",
            "Routine//Phase oversampling",
        ],
        "formula": lambda es, np, ap, op:
            1/(
                es * (np/ap) *
                (1 + float(op.split()[0])/100)
            )
    },
    # This is the echo spacing that would have resoluted in the
    # same amount of distortions if no acceleration/overampling
    # had been used
    "EffectiveEchoSpacing": {
        "args": ["BandwidthPerPixelPhaseEncode", "ReconMatrixPE"],
        "formula": lambda x, y: 1/(x*y)
    },
    # This should really be called "EffectiveTotalReadoutTime"
    "TotalReadoutTime": {
        "args": ["EffectiveEchoSpacing", "ReconMatrixPE"],
        "formula": lambda x, y: x * (y - 1)
    },
    "EchoTrainLength": {
        "args": [(
            "Sequence//EPI Factor",
            "Sequence - Part 1//EPI Factor",
        )]
    },
}
# TSE:
for key in ("tse*", "spc*"):
    KEYMAP_SPECIAL[key] = {
        "RepetitionTimePreparation": "VendorReportedRepetitionTime",
        "RepetitionTimeInversion": "VendorReportedRepetitionTime",
        "EchoTrainLength": {
            "args": [(
                "Sequence//Turbo Factor",
                "Sequence - Part 1//Turbo Factor",
            )]
        },
    }


def _make_mapper(mapper):
    if callable(mapper):
        # must be callable(bids, key, prot) -> bool
        return mapper

    if not isinstance(mapper, dict):
        # Direct mapping from protocol key to bids key
        mapper = {"args": [mapper], "formula": lambda x: x}

    def func(bids, key, prot):
        inp_args = mapper.get("args", [])
        inp_kwargs = mapper.get("kwargs", {})
        iadd = mapper.get('iadd', False)
        formula = mapper["formula"]
        # collect positional arguments
        args = []
        for items in inp_args:
            if not isinstance(items, tuple):
                items = (items,)
            # There can be multiple variants for each protocol key.
            # We try each variant sequentially until one works.
            exceptions = []
            for item in items:
                try:
                    if item in bids:
                        args.append(bids[item])
                    else:
                        args.append(_get(prot, item))
                    break
                except Exception as e:
                    exceptions.append(e)
            if len(exceptions) == len(items):
                raise exceptions
        # collect keyword arguments
        kwargs = {}
        for key, item in inp_kwargs.items():
            if not isinstance(items, tuple):
                items = (items,)
            # There can be multiple variants for each protocol key.
            # We try each variant sequentially until one works.
            exceptions = []
            for item in items:
                try:
                    if item in bids:
                        kwargs[key] = bids[item]
                    else:
                        kwargs[key] = _get(prot, item)
                    break
                except Exception as e:
                    exceptions.append(e)
            if len(exceptions) == len(items):
                raise exceptions
        # call formula
        if iadd:
            bids.setdefaut(key, [])
            bids[key] += formula(*args, **kwargs)
        else:
            bids[key] = formula(*args, **kwargs)
        return iadd

    return func


def _siemens_to_bids(bids, prot, keymap):
    for key, mappers in keymap.items():
        # There can be multiple mappers for a given keys
        # - if mappers implement `iadd=True`, the key contains a list
        #   that gets sequentially populated by each mapper;
        # - else, mappers are tried sequentially until one works.
        if not isinstance(mappers, list):
            mappers = [mappers]
        for mapper in mappers:
            try:
                if not callable(mapper):
                    mapper = _make_mapper(mapper)
                iadd = mapper(bids, key, prot)
                if not iadd:
                    break
            except Exception:
                continue
    return bids


def siemens_to_bids(prot, **kwargs):
    """
    Convert a parsed SIEMENS protocol into a BIDS sidecar
    """
    bids = {}
    vox2anat, anat2vox, shape = nii2axes(**kwargs)

    # Basic fields
    _siemens_to_bids(bids, prot, KEYMAP_BASIC)

    # Set fields based on nifti header
    if anat2vox is not None:
        if "DirectionFE" in bids:
            bids["FrequencyEncodingDirection"] = anat2vox["DirectionFE"]
            bids["ReconMatrixFE"] = {
                "i": shape[0],
                "j": shape[1],
                "k": shape[2],
            }[bids["FrequencyEncodingDirection"][0]]
        if "DirectionPE" in bids:
            bids["PhaseEncodingDirection"] = anat2vox["DirectionPE"]
            bids["ReconMatrixPE"] = {
                "i": shape[0],
                "j": shape[1],
                "k": shape[2],
            }[bids["PhaseEncodingDirection"][0]]
        if "DirectionSE" in bids:
            bids["SliceEncodingDirection"] = anat2vox["DirectionSE"]
            bids["ReconMatrixSE"] = {
                "i": shape[0],
                "j": shape[1],
                "k": shape[2],
            }[bids["SliceEncodingDirection"][0]]

    # Common fields
    _siemens_to_bids(bids, prot, KEYMAP_CLASSIC)

    # Guess recon matrix if file not available
    if anat2vox is None:
        itrp = _get(prot, "Resolution//Interpolation", None)
        if itrp is None:
            itrp = _get(prot, "Resolution - Common//Interpolation", None)
        try:
            bids["ReconMatrixFE"] = bids["AcqusitionMatrixFE"]
            if itrp == "On":
                bids["ReconMatrixFE"] *= 2
        except Exception:
            pass
        try:
            bids["ReconMatrixPE"] = bids["AcqusitionMatrixPE"]
            if itrp == "On":
                bids["ReconMatrixPE"] *= 2
        except Exception:
            pass
        try:
            bids["ReconMatrixSE"] = bids["AcqusitionMatrixSE"]
        except Exception:
            pass

    # Known sequences
    seqname = bids.get("SequenceName", None)
    if seqname:
        for seqpattern, keymap in KEYMAP_SPECIAL.items():
            if fnmatch.filter([seqname], seqpattern):
                _siemens_to_bids(bids, prot, keymap)
    return bids
