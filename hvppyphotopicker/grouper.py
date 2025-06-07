import os

class PhotoGrouper:
    def __init__(self, image_paths, threshold_seconds=3.0):
        self.image_paths = sorted(image_paths)
        self.threshold = threshold_seconds
        self.groups = self._group_images()

    def _group_images(self):
        groups = []
        current_group = []
        prev_time = None

        for path in self.image_paths:
            try:
                mtime = os.path.getmtime(path)
            except:
                continue

            if not prev_time or (mtime - prev_time <= self.threshold):
                current_group.append(path)
            else:
                groups.append(current_group)
                current_group = [path]

            prev_time = mtime

        if current_group:
            groups.append(current_group)

        return groups