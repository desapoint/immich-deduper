import glob
import os

from conf import envs


def model():
    checkpointDir = os.path.join(envs.ddupData, 'models', 'checkpoints')
    matches = sorted(glob.glob(os.path.join(checkpointDir, 'resnet152-*.pth')))
    if matches:
        return True, ['Model weights found locally', f'Path: {matches[-1]}']

    if envs.offline:
        return False, [
            'Offline mode enabled but ResNet152 weights were not found',
            f'Expected under: {checkpointDir}',
            'Download the ResNet152 torchvision weights before processing assets.',
        ]

    return True, [
        'Model weights are not cached yet',
        'They will download and load on the first vector-processing task.',
    ]
