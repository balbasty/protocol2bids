import nibabel as nib
import numpy as np


def nii2shape(file=None, shape=None, affine=None):
    if file is not None:
        f = nib.load(file)
        if shape is None:
            shape = f.shape[:3]
        if affine is None:
            affine = f.affine
    return affine, shape


def nii2axes(**kwargs):
    """
    Compute mappings between voxel (ijk) and anatomical (RAS) axes

    Parameters
    ----------
    file : path-like, optional
        Path to nifti file
    affine : (4, 4) array, optional
        Affine matrix
    shape : list[int], optional
        Volume shape

    Returns
    -------
    vox2anat : (3,) list[{"LR", "RL", "AP", "PA", "IS", "SI}]
        Anatomical axis and polarity of each voxel axis
    anat2vox : dict[str, str]
        Voxel axis and polarity of each anatomical axis.
        Keys are in `{"LR", "RL", "AP", "PA", "IS", "SI"}`
        Values are in `{"i+", "i-", "j+", "j-", "k+", "k-"}`
    shape : list[int], optional
        Volume shape
    """
    affine, shape = nii2shape(**kwargs)

    if affine is None or shape is None:
        return None, None, None

    affine = affine[:3, :3]
    voxel_size = (affine**2).sum(0)**0.5
    affine = affine / voxel_size

    # add noise to avoid issues if there's a 45 deg angle somewhere
    affine = affine + (np.random.random([3, 3]) - 0.5) * 1e-5

    # project onto canonical axes
    onehot = np.round(np.square(affine)).astype(np.int32)
    index = [
        onehot[:, 0].tolist().index(1),
        onehot[:, 1].tolist().index(1),
        onehot[:, 2].tolist().index(1),
    ]
    sign = [
        -1 if affine[index[0], 0] < 0 else 1,
        -1 if affine[index[1], 1] < 0 else 1,
        -1 if affine[index[2], 2] < 0 else 1,
    ]
    anatnames = ['LR', 'PA', 'IS']
    voxnames = ['i', 'j', 'k']

    vox2anat = [
        anatnames[index[0]][::-1] if sign[0] else index[0],
        anatnames[index[1]][::-1] if sign[1] else index[1],
        anatnames[index[2]][::-1] if sign[2] else index[2],
    ]
    anat2vox = {}
    if 'LR' in vox2anat:
        anat2vox['LR'] = voxnames[vox2anat.index('LR')] + '+'
        anat2vox['RL'] = voxnames[vox2anat.index('LR')] + '-'
    else:
        anat2vox['RL'] = voxnames[vox2anat.index('RL')] + '+'
        anat2vox['LR'] = voxnames[vox2anat.index('RL')] + '-'
    if 'PA' in vox2anat:
        anat2vox['PA'] = voxnames[vox2anat.index('PA')] + '+'
        anat2vox['AP'] = voxnames[vox2anat.index('PA')] + '-'
    else:
        anat2vox['AP'] = voxnames[vox2anat.index('AP')] + '+'
        anat2vox['PA'] = voxnames[vox2anat.index('AP')] + '-'
    if 'IS' in vox2anat:
        anat2vox['IS'] = voxnames[vox2anat.index('IS')] + '+'
        anat2vox['SI'] = voxnames[vox2anat.index('IS')] + '-'
    else:
        anat2vox['SI'] = voxnames[vox2anat.index('SI')] + '+'
        anat2vox['IS'] = voxnames[vox2anat.index('SI')] + '-'

    return vox2anat, anat2vox, shape
