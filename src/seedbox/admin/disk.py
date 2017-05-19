from seedbox import models
from .base import ModelView


class DiskView(ModelView):
    column_list = [
        'node',
        'device',
        'wipe_next_boot',
    ]

    column_labels = {
        'sector_size_bytes': "Size of a sector (bytes)",
    }
    column_descriptions = {
        'device': "E.g. /dev/sda.",
        'wipe_next_boot': "If this is set, disk partition table will be wiped on next boot.",
        'sector_size_bytes': "Usually it equals 512.",
    }
    inline_models = [
        (models.DiskPartition, {
            'column_labels': {
                'size_mibs': "Size (MiB)",
            },
            'column_descriptions': {
                'number': "The partition number in the partition table (one - indexed).",
                'label': "Label for partition and filesystem.",
                'size_mibs': "If not set, the partition will fill the remainder of the disk.",
                'format': "Filesystem format (ext4, btrfs, or xfs).",
            }
        }),
    ]

    def on_model_change(self, form, model, is_created):
        model.node.target_config_version += 1
        self.session.add(model.node)
